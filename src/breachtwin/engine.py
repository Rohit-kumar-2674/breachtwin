"""Execute explicit contracts using in-process ASGI requests, with fresh app state."""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import inspect
import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi.testclient import TestClient

from . import __version__
from .contract import Assertion, Contract, EnvRef


def load_factory(reference: str):
    if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*", reference):
        raise ValueError("Factory must be an explicit module:function reference")
    module, name = reference.split(":")
    factory = getattr(importlib.import_module(module), name)
    if not callable(factory):
        raise ValueError("Factory must be callable and return a fresh ASGI application")
    return factory


def _headers(actor):
    result = {}
    for key, value in actor.headers.items():
        if isinstance(value, EnvRef):
            if value.env not in os.environ:
                raise ValueError("Missing an environment variable required by the contract")
            value = os.environ[value.env]
        if "\r" in value or "\n" in value:
            raise ValueError("Invalid credential header value")
        result[key] = value
    return result


def _lookup(data, dotted):
    for part in dotted.split('.'):
        if isinstance(data, dict) and part in data:
            data = data[part]
        elif isinstance(data, list) and part.isdigit() and int(part) < len(data):
            data = data[int(part)]
        else:
            return False, None
    return True, data


def _equal(actual, expected):
    # Python equates True and 1; JSON security assertions must distinguish them.
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_equal(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def matches(assertion: Assertion, status: int, data) -> bool:
    if assertion.status and status not in assertion.status:
        return False
    for key, expected in assertion.json_equals.items():
        present, value = _lookup(data, key)
        if not present or not _equal(value, expected):
            return False
    return True


def run_contract(contract: Contract, factory_ref: str, *, label: str = "Assessment") -> dict:
    factory = load_factory(factory_ref)
    headers = {name: _headers(actor) for name, actor in contract.actors.items()}
    started = perf_counter()
    results = []
    for experiment in contract.experiments:
        observations = []
        controls_ok = True
        probe_verdicts = []
        aborted = False
        try:
            # The context runs ASGI lifespan; the factory resets the fixture per experiment.
            with TestClient(factory(), base_url="http://breachtwin.test", raise_server_exceptions=False, follow_redirects=False) as client:
                for step in experiment.steps:
                    if aborted:
                        observations.append({"name": step.name, "kind": step.kind, "actor": step.actor, "method": step.method, "path": step.path, "outcome": "skipped", "status": None, "duration_ms": 0, "expected_matched": False, "violation_matched": False})
                        continue
                    tick = perf_counter()
                    # Each request uses its own actor's supplied headers. Never share login cookies.
                    client.cookies.clear()
                    kwargs = {"headers": headers[step.actor]}
                    if step.body is not None:
                        kwargs["json"] = step.body
                    response = client.request(step.method, step.path, **kwargs)
                    try:
                        data = response.json()
                    except ValueError:
                        data = None
                    expected = matches(step.expect, response.status_code, data)
                    violation = step.violation is not None and matches(step.violation, response.status_code, data)
                    if step.kind == "probe":
                        # Evidence of a forbidden result takes precedence, even with a denial code.
                        outcome = "reproduced" if violation else "blocked" if expected else "inconclusive"
                        probe_verdicts.append(outcome)
                    else:
                        outcome = "passed" if expected else "failed"
                        if not expected:
                            controls_ok = False
                            aborted = True
                    observations.append({"name": step.name, "kind": step.kind, "actor": step.actor, "method": step.method, "path": step.path, "outcome": outcome, "status": response.status_code, "duration_ms": round((perf_counter()-tick)*1000, 3), "expected_matched": expected, "violation_matched": bool(violation)})
        except Exception as exc:
            # Exception strings can contain response bodies or credentials; record the type only.
            controls_ok = False
            remaining = experiment.steps[len(observations):]
            observations.append({"name": "Application or lifecycle error", "kind": "error", "outcome": "failed", "error_type": type(exc).__name__, "status": None, "duration_ms": 0})
            for step in remaining:
                observations.append({"name": step.name, "kind": step.kind, "actor": step.actor, "method": step.method, "path": step.path, "outcome": "skipped", "status": None, "duration_ms": 0, "expected_matched": False, "violation_matched": False})
        if not controls_ok or not probe_verdicts:
            verdict = "inconclusive"
        elif "reproduced" in probe_verdicts:
            verdict = "reproduced"
        elif "inconclusive" in probe_verdicts:
            verdict = "inconclusive"
        else:
            verdict = "blocked"
        results.append({"id": experiment.id, "title": experiment.title, "rule": experiment.rule, "cwe": experiment.cwe, "remediation": experiment.remediation, "verdict": verdict, "controls_ok": controls_ok, "steps": observations})
    source_hash = None
    try:
        source_hash = hashlib.sha256(Path(inspect.getfile(factory)).read_bytes()).hexdigest()
    except (OSError, TypeError):
        pass
    packages = {}
    for name in ("fastapi", "starlette", "httpx", "pydantic", "anyio"):
        packages[name] = importlib.metadata.version(name)
    return {
        "run_id": uuid4().hex[:12], "created_at": datetime.now(timezone.utc).isoformat(),
        "label": label, "factory": factory_ref, "contract": contract.model_dump(mode="json"),
        "environment": {"breachtwin": __version__, "python": platform.python_version(), "platform": platform.system(), "packages": packages, "factory_module_sha256": source_hash},
        "results": results, "duration_ms": round((perf_counter()-started)*1000, 3),
        "summary": {s: sum(r["verdict"] == s for r in results) for s in ("reproduced", "blocked", "inconclusive")},
        "scope": "Explicit contract cases on a trusted, fresh local ASGI fixture. No network scanning. This is not a proof of application-wide security.",
    }


def exit_status(payload: dict) -> int:
    if payload["summary"]["inconclusive"]:
        return 2
    return 1 if payload["summary"]["reproduced"] else 0
