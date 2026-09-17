"""Versioned evidence with an integrity checksum, never an authenticity claim."""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from .contract import Contract


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def bundle(payload: dict) -> dict:
    return {"format": "breachtwin.evidence", "schema_version": 1, "payload": payload,
            "integrity": {"algorithm": "sha256", "digest": hashlib.sha256(canonical(payload)).hexdigest()}}


def verify_bundle(value: dict) -> dict:
    try:
        if value["format"] != "breachtwin.evidence" or value["schema_version"] != 1:
            raise ValueError("Unsupported evidence format or schema version")
        if value["integrity"]["algorithm"] != "sha256":
            raise ValueError("Unsupported integrity algorithm")
        digest = hashlib.sha256(canonical(value["payload"])).hexdigest()
        if not hmac.compare_digest(digest, value["integrity"]["digest"]):
            raise ValueError("Evidence checksum mismatch; the payload was changed or corrupted")
        payload = value["payload"]
        contract = Contract.model_validate(payload["contract"])
        if [r["id"] for r in payload["results"]] != [e.id for e in contract.experiments]:
            raise ValueError("Evidence cases do not match the contract")
        summary = {s: sum(r["verdict"] == s for r in payload["results"]) for s in ("reproduced", "blocked", "inconclusive")}
        if summary != payload["summary"] or sum(summary.values()) != len(payload["results"]):
            raise ValueError("Evidence contains inconsistent verdicts")
        for key in ("environment", "factory", "run_id", "created_at", "label", "duration_ms", "scope"):
            if key not in payload:
                raise ValueError("Evidence is missing required metadata")
        return payload
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Malformed evidence bundle") from exc


def read_bundle(path: str | Path) -> dict:
    raw = Path(path).read_bytes()
    if len(raw) > 10_485_760:
        raise ValueError("Evidence exceeds the 10 MiB limit")
    value = json.loads(raw)
    verify_bundle(value)
    return value


def write_bundle(path: str | Path, value: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def export_regression(value: dict, factory: str, path: str | Path) -> None:
    payload = verify_bundle(value)
    contract_json = json.dumps(payload["contract"], ensure_ascii=True)
    text = f'''"""Generated BreachTwin regression test. Requires the breachtwin package.

Run: python {Path(path).name}
Override the trusted application factory with BREACHTWIN_FACTORY.
This file contains synthetic fixtures and unresolved environment references.
"""
import json
import os
import unittest

from breachtwin.contract import Contract
from breachtwin.engine import run_contract

CONTRACT = Contract.model_validate(json.loads({contract_json!r}))
FACTORY = os.environ.get("BREACHTWIN_FACTORY", {factory!r})


class SecurityRegression(unittest.TestCase):
    def test_access_boundaries(self):
        result = run_contract(CONTRACT, FACTORY, label="Regression")
        for case in result["results"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["verdict"], "blocked", case["title"] + ": " + case["verdict"])
                self.assertTrue(case["controls_ok"], "A legitimate workflow failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
