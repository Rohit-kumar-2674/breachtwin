"""Generated BreachTwin regression test. Requires the breachtwin package.

Run: python test_regression.py
Override the trusted application factory with BREACHTWIN_FACTORY.
This file contains synthetic fixtures and unresolved environment references.
"""
import json
import os
import unittest

from breachtwin.contract import Contract
from breachtwin.engine import run_contract

CONTRACT = Contract.model_validate(json.loads('{"schema_version": 1, "name": "Organization access boundaries", "description": "Three repeatable access-control experiments using synthetic organizations, users, and records.", "actors": {"alice": {"headers": {"X-Lab-User": "alice"}}, "bob": {"headers": {"X-Lab-User": "bob"}}, "maya": {"headers": {"X-Lab-User": "maya"}}, "admin": {"headers": {"X-Lab-User": "admin"}}}, "experiments": [{"id": "BT-001", "title": "Organization isolation", "rule": "A member can read their own organization\'s records and cannot read another organization\'s records.", "cwe": "CWE-639", "remediation": "Scope record access to the current principal\'s organization before returning data. Repeat the foreign-record probe and the own-record controls.", "steps": [{"name": "Alice reads an Alpha record", "kind": "control", "actor": "alice", "method": "GET", "path": "/records/doc-alpha", "body": null, "expect": {"status": [200], "json_equals": {"id": "doc-alpha", "organization": "alpha"}}, "violation": null}, {"name": "Alice requests a Bravo record", "kind": "probe", "actor": "alice", "method": "GET", "path": "/records/doc-bravo", "body": null, "expect": {"status": [403, 404], "json_equals": {}}, "violation": {"status": [], "json_equals": {"id": "doc-bravo", "organization": "bravo", "content": "SYNTHETIC BRAVO RECORD"}}}, {"name": "Bob can still read his Bravo record", "kind": "control", "actor": "bob", "method": "GET", "path": "/records/doc-bravo", "body": null, "expect": {"status": [200], "json_equals": {"id": "doc-bravo", "organization": "bravo"}}, "violation": null}]}, {"id": "BT-002", "title": "Membership revocation", "rule": "A revoked member loses record access immediately; other active members retain access.", "cwe": "CWE-863", "remediation": "Recheck current membership for every protected operation. In a real token-based app, also test stale sessions and credential expiry with explicit fixtures.", "steps": [{"name": "Maya reads a record before revocation", "kind": "control", "actor": "maya", "method": "GET", "path": "/records/doc-alpha", "body": null, "expect": {"status": [200], "json_equals": {"id": "doc-alpha"}}, "violation": null}, {"name": "Administrator revokes Maya\'s membership", "kind": "setup", "actor": "admin", "method": "POST", "path": "/admin/members/maya/revoke", "body": null, "expect": {"status": [200], "json_equals": {"revoked": true, "member": "maya"}}, "violation": null}, {"name": "Maya requests the record after revocation", "kind": "probe", "actor": "maya", "method": "GET", "path": "/records/doc-alpha", "body": null, "expect": {"status": [401, 403, 404], "json_equals": {}}, "violation": {"status": [], "json_equals": {"id": "doc-alpha", "content": "SYNTHETIC ALPHA RECORD"}}}, {"name": "Alice retains access to the Alpha record", "kind": "control", "actor": "alice", "method": "GET", "path": "/records/doc-alpha", "body": null, "expect": {"status": [200], "json_equals": {"id": "doc-alpha"}}, "violation": null}]}, {"id": "BT-003", "title": "Restricted administrator action", "rule": "Only an administrator may create an administrative report; member record access remains available.", "cwe": "CWE-862", "remediation": "Enforce administrator authorization on the report endpoint before creating the report. Keep the administrator success control and the regular member read control.", "steps": [{"name": "Administrator creates a report", "kind": "control", "actor": "admin", "method": "POST", "path": "/admin/reports", "body": null, "expect": {"status": [201], "json_equals": {"created": true, "created_by": "admin"}}, "violation": null}, {"name": "A regular member requests a report", "kind": "probe", "actor": "alice", "method": "POST", "path": "/admin/reports", "body": null, "expect": {"status": [403], "json_equals": {}}, "violation": {"status": [], "json_equals": {"created": true, "created_by": "alice"}}}, {"name": "Alice retains regular record access", "kind": "control", "actor": "alice", "method": "GET", "path": "/records/doc-alpha", "body": null, "expect": {"status": [200], "json_equals": {"id": "doc-alpha"}}, "violation": null}]}]}'))
FACTORY = os.environ.get("BREACHTWIN_FACTORY", 'breachtwin.lab:create_fixed_app')


class SecurityRegression(unittest.TestCase):
    def test_access_boundaries(self):
        result = run_contract(CONTRACT, FACTORY, label="Regression")
        for case in result["results"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["verdict"], "blocked", case["title"] + ": " + case["verdict"])
                self.assertTrue(case["controls_ok"], "A legitimate workflow failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
