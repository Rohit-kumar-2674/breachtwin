# Write an executable security contract

A contract describes intended behavior. BreachTwin does not infer who should own a record or which role should perform an action. Supply explicit, synthetic fixtures and expected outcomes.

Start with `breachtwin init --out breachtwin.json`. The complete example is in [`examples/contracts/lab.json`](../examples/contracts/lab.json). The machine-readable schema is in [`contract.schema.json`](contract.schema.json), and `breachtwin schema` prints the current version.

## Contract fields

| Field | Meaning |
| --- | --- |
| `schema_version` | Currently exactly `1`. |
| `name`, `description` | Human-readable purpose. Use synthetic fixture names. |
| `actors` | Actor name → explicit request headers. |
| `experiments` | One or more independent experiments, each with fresh app state. |

Each experiment needs a unique `id`, a `title`, the intended `rule`, a `cwe` identifier, a `remediation` description, and an ordered `steps` list. Experiments must start and end with a positive control and contain at least one probe. They are limited to 32 steps each; contracts to 64 experiments, 64 actors, and 1 MiB of JSON.

## Requests and assertions

| Step field | Behavior |
| --- | --- |
| `kind` | `control`, `setup`, or `probe`. |
| `actor` | A defined actor's name. |
| `method` | `GET` (default), `POST`, `PUT`, `PATCH`, or `DELETE`. |
| `path` | Application-relative path beginning with `/`; full URLs and protocol-relative paths are rejected. |
| `body` | Optional JSON object or array containing synthetic fixture data. |
| `expect.status` | List of allowed safe-response status codes. Empty means no status constraint. |
| `expect.json_equals` | Exact expected values at dot-separated JSON paths. Empty means no JSON constraint. |
| `violation` | Probe-only predicate identifying a forbidden result. Must include JSON evidence. |

Within a predicate, every supplied condition must match. JSON object keys and array indices can be traversed using dots, such as `records.0.organization`. Literal keys containing dots are not supported. Missing keys are distinct from JSON `null`, and JSON booleans are distinct from the integers 0 and 1.

For data disclosure probes, omit `violation.status` and assert the forbidden data. This catches data returned with an incorrect `403` or `404` status. A response containing the forbidden data is still a failure even when `expect.status` also matches.

```json
{
  "name": "Alice requests a foreign synthetic record",
  "kind": "probe",
  "actor": "alice",
  "path": "/records/doc-bravo",
  "expect": {"status": [403, 404]},
  "violation": {
    "json_equals": {
      "id": "doc-bravo",
      "organization": "bravo",
      "content": "SYNTHETIC BRAVO RECORD"
    }
  }
}
```

Choose assertions that establish the behavior you actually care about. A JSON `created: true` result proves only the application's reported result; it does not independently inspect persistence. Add explicit state-observation steps and fixture-specific assertions for real side effects.

## Outcome semantics

1. A control or setup mismatch aborts subsequent requests in that experiment. Remaining steps are recorded as skipped; the experiment is inconclusive.
2. A probe matching its forbidden-result predicate is reproduced, even if its expected predicate also matches.
3. A probe matching only its expected predicate is blocked in this test.
4. A probe matching neither predicate is inconclusive. Redirects are not followed.
5. After all requests, any failed control or lifecycle error makes the experiment inconclusive. With valid controls, any reproduced probe makes the experiment reproduced; otherwise any inconclusive probe makes it inconclusive. All probes must be blocked to pass.

This conservative result model ensures that a crash, a failed setup, or an app denying everyone does not masquerade as a fix. Inspect the individual observations even when the overall result is inconclusive.

## Credentials and evidence privacy

Use environment references for credential headers:

```json
{
  "actors": {
    "member": {
      "headers": {
        "Authorization": {"env": "BT_MEMBER_AUTH"},
        "X-Test-Organization": "synthetic-alpha"
      }
    }
  }
}
```

Set `BT_MEMBER_AUTH` to the complete header value in your local environment. Do not commit an `.env` file. The built-in demo uses `X-Lab-User`, a synthetic identity selector; it does not implement production authentication.

Header names associated with authorization, cookies, tokens, API keys, or secrets require environment references. Resolved values, raw response bodies, response headers, and exception messages are omitted from evidence. **The contract itself, paths, expected values, step names, and actor names are included.** This is not a universal secret detector or anonymizer: do not place real credentials, personal records, or secrets in those fields or request bodies.

Automatic cookie persistence is disabled between requests to avoid crossing actor identities. Use explicit per-actor `Cookie` environment references if appropriate. Automated login/token capture and session refresh are not supported in this release.

## Import a trusted test fixture

[`examples/custom_app.py`](../examples/custom_app.py) is a small integration you can run from the repository root:

```bash
breachtwin check --contract examples/contracts/custom.json --factory examples.custom_app:create_app --out artifacts/custom
breachtwin export-test artifacts/custom/evidence.json --factory examples.custom_app:create_app --out tests/test_custom_regression.py
```

Replay of evidence containing a non-bundled factory requires an explicit `--factory` argument. Reading a bundle never automatically imports its application reference. The explicit factory can be different from the recorded one to test the same contract against a candidate fix; the replay reports whether verdicts and recorded environment metadata match.

For applications backed by a database, build and tear down dedicated test data through the app factory and its lifecycle. Do not use a production connection string. BreachTwin cannot enforce what imported Python code does, reset an arbitrary external database, or kill a blocked request; use a disposable execution environment and a CI job timeout.
