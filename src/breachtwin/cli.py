"""CLI. Explicit trusted factories, local ASGI transport, and meaningful exit codes."""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path

from pydantic import ValidationError

from . import __version__
from .contract import Contract, load_contract
from .engine import exit_status, run_contract
from .evidence import bundle, export_regression, read_bundle, write_bundle
from .report import write_report

BUILTINS = {"breachtwin.lab:create_fixed_app", "breachtwin.lab:create_vulnerable_app"}


def builtin_contract():
    return Contract.model_validate_json(files("breachtwin").joinpath("assets/lab.json").read_text(encoding="utf-8"))


def summary(payload):
    print(f"\nBreachTwin {__version__} | {payload['label']}")
    for result in payload["results"]:
        print(f"  {result['id']}  {result['verdict'].upper():14} {result['title']}")
    counts = payload["summary"]
    print(f"  {counts['reproduced']} reproduced | {counts['blocked']} blocked | {counts['inconclusive']} inconclusive")


def save_run(payload, out):
    value = bundle(payload)
    write_bundle(out / "evidence.json", value)
    write_report([value], out / "report.html")
    return value


def selected_factory(args, payload):
    if args.factory:
        return args.factory
    if payload["factory"] in BUILTINS:
        return payload["factory"]
    raise ValueError("For external evidence, supply --factory module:function for a local application you trust")


class ReportHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, report_path, **kwargs):
        self.report_path = report_path
        super().__init__(*args, **kwargs)

    def do_GET(self):
        host = self.headers.get("Host", "")
        if host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
            self.send_error(403)
            return
        if self.path not in {"/", "/report.html"}:
            self.send_error(404)
            return
        data = self.report_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def parser():
    p = argparse.ArgumentParser(prog="breachtwin", description="Reproduce, inspect, and regression-test local access-control failures.")
    p.add_argument("--version", action="version", version=f"BreachTwin {__version__}")
    commands = p.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Compare the bundled vulnerable and fixed synthetic applications")
    demo.add_argument("--out", type=Path, default=Path("artifacts/demo"))
    check = commands.add_parser("check", help="Run a contract against an explicitly trusted ASGI factory")
    check.add_argument("--contract", type=Path, required=True)
    check.add_argument("--factory", required=True, help="Trusted importable module:function; returns fresh app state")
    check.add_argument("--out", type=Path, default=Path("artifacts/check"))
    replay = commands.add_parser("replay", help="Verify evidence and rerun its contract on a fresh app")
    replay.add_argument("evidence", type=Path)
    replay.add_argument("--factory")
    replay.add_argument("--out", type=Path, default=Path("artifacts/replay"))
    verify = commands.add_parser("verify", help="Check evidence integrity without importing any application")
    verify.add_argument("evidence", type=Path)
    export = commands.add_parser("export-test", help="Export a unittest regression file from recorded evidence")
    export.add_argument("evidence", type=Path)
    export.add_argument("--factory")
    export.add_argument("--out", type=Path, default=Path("test_breachtwin_regression.py"))
    validate = commands.add_parser("validate", help="Validate a contract without importing an application")
    validate.add_argument("contract", type=Path)
    init = commands.add_parser("init", help="Write the example contract to start a local integration")
    init.add_argument("--out", type=Path, default=Path("breachtwin.json"))
    schema = commands.add_parser("schema", help="Print the JSON Schema for contracts")
    view = commands.add_parser("view", help="Serve only a saved report on 127.0.0.1")
    view.add_argument("report", type=Path, nargs="?", default=Path("artifacts/demo/report.html"))
    view.add_argument("--port", type=int, default=8787)
    view.add_argument("--open", action="store_true", help="Open the report in the system browser")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "demo":
            contract = builtin_contract()
            values = []
            for mode in ("vulnerable", "fixed"):
                payload = run_contract(contract, f"breachtwin.lab:create_{mode}_app", label=mode.title())
                values.append(save_run(payload, args.out / mode))
                summary(payload)
            write_report(values, args.out / "report.html")
            export_regression(values[1], "breachtwin.lab:create_fixed_app", args.out / "test_regression.py")
            print(f"\nReport: {args.out / 'report.html'}\nRegression: {args.out / 'test_regression.py'}")
            # A demo succeeds only when it reproduces every seeded bug and validates every fix.
            total = len(contract.experiments)
            return 0 if values[0]["payload"]["summary"]["reproduced"] == total and values[1]["payload"]["summary"]["blocked"] == total else 2
        if args.command == "check":
            payload = run_contract(load_contract(args.contract), args.factory)
            save_run(payload, args.out)
            summary(payload)
            print(f"Report: {args.out / 'report.html'}")
            return exit_status(payload)
        if args.command == "replay":
            old = read_bundle(args.evidence)
            factory = selected_factory(args, old["payload"])
            payload = run_contract(Contract.model_validate(old["payload"]["contract"]), factory, label="Replay")
            payload["replay_of"] = old["payload"]["run_id"]
            payload["recorded_verdicts_match"] = [r["verdict"] for r in payload["results"]] == [r["verdict"] for r in old["payload"]["results"]]
            payload["recorded_environment_matches"] = payload["environment"] == old["payload"]["environment"]
            save_run(payload, args.out)
            summary(payload)
            print(f"Recorded verdicts match: {payload['recorded_verdicts_match']}; environment matches: {payload['recorded_environment_matches']}")
            return exit_status(payload)
        if args.command == "verify":
            value = read_bundle(args.evidence)
            print(f"Checksum and structure verified: {value['payload']['run_id']}\nA checksum detects changes; it does not authenticate the author or prove the findings.")
        elif args.command == "export-test":
            value = read_bundle(args.evidence)
            export_regression(value, selected_factory(args, value["payload"]), args.out)
            print(f"Regression test written: {args.out}")
        elif args.command == "validate":
            contract = load_contract(args.contract)
            print(f"Valid contract: {contract.name} ({len(contract.experiments)} experiments)")
        elif args.command == "init":
            if args.out.exists():
                raise ValueError("Output already exists; choose a new path with --out")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(builtin_contract().model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
            print(f"Contract written: {args.out}")
        elif args.command == "schema":
            print(json.dumps(Contract.model_json_schema(), indent=2))
        elif args.command == "view":
            if not args.report.is_file() or args.report.suffix.lower() != ".html":
                raise ValueError("Choose an existing .html report")
            handler = partial(ReportHandler, report_path=args.report.resolve())
            with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
                address = f"http://127.0.0.1:{server.server_port}"
                print(f"Report: {address}\nRead-only report viewer. Press Ctrl+C to stop.", flush=True)
                if args.open:
                    webbrowser.open(address)
                server.serve_forever()
        return 0
    except ValidationError as exc:
        print("Invalid contract or evidence:", file=sys.stderr)
        for error in exc.errors(include_input=False, include_context=False, include_url=False)[:8]:
            print(f"  {'.'.join(map(str, error['loc']))}: {error['msg']}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        print(f"BreachTwin: {exc}", file=sys.stderr)
        return 2
    except (ImportError, AttributeError, TypeError) as exc:
        print(f"BreachTwin: could not load the trusted factory ({type(exc).__name__}). Check --factory and your virtual environment.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
