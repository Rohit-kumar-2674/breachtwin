# Initial release validation

Validated on 2026-09-16 using Linux and Python 3.12.14. The exact installed Python package snapshot is in [`requirements-tested.txt`](../requirements-tested.txt).

## Recorded results

| Check | Observed result |
| --- | --- |
| Automated Python suite | 38 tests passed. |
| Vulnerable synthetic lab | All 3 seeded contract violations reproduced; all 6 positive controls passed. |
| Fixed synthetic lab | All 3 probes blocked; all 6 positive controls passed. |
| Exported regression against fixed app | Passed. |
| Exported regression with vulnerable factory | Failed with 3 failing subtests, as expected. |
| Custom application example | Its independent note-ownership contract passed. |
| Fresh app state and ASGI lifespan | Verified per experiment and across repeated runs. |
| Outage / deny-all / failed startup | Inconclusive, never a passing assessment. |
| Failed revocation setup | Remaining steps skipped; result inconclusive. |
| Forbidden data with HTTP 403 | Reproduced; a denial code does not hide matched disclosure evidence. |
| Redirects / unexpected JSON / HTTP 500 | Inconclusive when neither expected nor violation predicates match. |
| Actor cookie separation | Cookies from one actor were not reused for another. |
| Credential handling | Environment secrets and response header secrets were absent from serialized evidence. |
| Evidence alteration | Payload changes rejected by checksum verification. |
| External evidence replay | Requires an explicitly supplied trusted application factory. |
| Local request transport | The demo passed with outbound socket connection creation instrumented to fail. |
| Report server | Requested report served; unrelated paths rejected with 404; unexpected Host rejected with 403. |
| Python packaging | Source distribution and wheel built; the wheel's demo ran outside the source checkout. |

The test run reported one upstream deprecation warning from Starlette's use of an AnyIO alias. No tests failed. This is documented rather than suppressed.

## Browser checks

The standalone report was opened from a local file in headless Chromium 153.0.8010.0 using Playwright. Checks covered:

- Switching between vulnerable and fixed recorded runs.
- Accurate outcome and positive-control counts.
- Outcome filtering, search, empty results, and clearing filters.
- Expanding experiments and playing a clearly labeled recorded trace.
- Downloading evidence JSON and verifying it with the CLI.
- Clipboard feedback and its manual-copy fallback.
- No horizontal page overflow at widths 320, 390, 768, and 1440 pixels.
- No uncaught JavaScript errors and no external report requests.

The desktop and mobile screenshots in this directory were generated from actual recorded evidence. The report makes no request to an external font, CDN, API, or analytics service. Viewport checks are not physical Android/iOS device testing.

## Scope of these results

These seeded examples validate the implemented experiment runner. They do not measure general vulnerability discovery, production security, zero false positives, or universal fix correctness. No external website or user infrastructure was assessed.

The GitHub Actions matrix is configured but was not run remotely before repository publication. Windows, macOS, Python 3.10/3.13, and native Termux runtime support are not claimed as locally verified.

To repeat the core checks:

```bash
python -m pytest -q
breachtwin demo
python artifacts/demo/test_regression.py
breachtwin verify artifacts/demo/fixed/evidence.json
```
