# Troubleshooting

| Symptom | What to check |
| --- | --- |
| `breachtwin: command not found` | Activate the environment or use its Python directly: `python -m breachtwin`. Install with `python -m pip install -e .` from the repository root. |
| `No module named breachtwin` | The terminal is using a different Python environment. Run `python -m pip show breachtwin` with the same interpreter. |
| `could not load the trusted factory` | Use `module:function`, not a filesystem path. Install your application package or run from a location where it is importable. Factories must accept no arguments. |
| `Invalid contract` | Run `breachtwin validate your-contract.json`. Fix the listed field; compare with `examples/contracts/custom.json`. |
| Missing environment variable | Supply the complete header value through the environment name in the actor's `env` reference. Never put the resolved secret in the JSON contract. |
| All cases inconclusive | Inspect the first failed positive control. Common causes include wrong routes, fixture identities, credentials, startup failures, or an app that denies all users. |
| An HTTP 500 or redirect is inconclusive | The response establishes neither the intended denial nor the forbidden JSON result. Investigate it; redirects are not followed. |
| A 403 is still reproduced | The forbidden-result predicate matched response JSON. Returning protected data with a denial status is still a disclosure. |
| Regression test exits with code 1 | `unittest` found reproduced/inconclusive cases, or the trusted app could not be loaded. Read the subtest output. |
| `check` exits with code 2 | The assessment is invalid or at least one case is inconclusive. A nonzero code is intentional for CI. |
| Report shows old results | The HTML is a saved recording. Rerun `check` or `demo`, then reopen the generated file. Trace playback only animates recorded events. |
| Clipboard button does not copy from a local file | The report exposes a selected text box for manual copying when the browser blocks clipboard access. |
| Viewer port already in use | Run `breachtwin view --port 8788`. |
| Phone cannot reach a remote machine's `127.0.0.1` | Loopback refers to the device itself. Download the HTML report or use a trusted SSH tunnel. The viewer intentionally has no public bind option. |
| Pydantic compilation fails in native Termux | This installation path has not been verified. Use Debian/Ubuntu or a remote Python environment with matching wheels; native Android may need Rust and compiler dependencies. |
| Request hangs | This release does not forcibly terminate in-process code. Interrupt it, inspect the fixture, and set an external CI job timeout. |
| Checksum mismatch | Retain the original file and regenerate evidence from the intended application. Do not edit evidence to make a failed test appear successful. |

## Reproduce a problem

Create a synthetic fixture and a minimal contract. Include the BreachTwin and Python versions, platform, expected behavior, actual verdict, and a redacted trace. Do not publish real access tokens, private records, or confidential application source in a public issue. Use the [security policy](../SECURITY.md) for security issues.

## Publish your copy on GitHub

Create an empty repository named `breachtwin` in your account. Do not initialize another README or license if importing this source. Then, from the extracted project folder:

```bash
git init -b main
git add .
git commit -m "Release BreachTwin 0.1.0: reproducible access-control experiments"
git remote add origin https://github.com/YOUR_USERNAME/breachtwin.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your account. If you are using an existing Git checkout, reuse its history and remote instead of reinitializing. Authenticate through your normal GitHub workflow; do not place a token in the remote URL, README, or contract. After pushing, inspect the Actions tab before claiming cross-platform CI results.
