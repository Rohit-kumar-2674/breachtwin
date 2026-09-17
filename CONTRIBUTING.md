# Contributing

BreachTwin values evidence that another developer can reproduce.

1. Install an editable development environment: `python -m pip install -e ".[dev]"`.
2. Create a branch describing one concrete change.
3. Include a synthetic failing fixture, a corrected fixture, and checks for legitimate behavior when changing verdict logic.
4. Run `python -m pytest -q`, `breachtwin demo`, and the generated regression test.
5. For report changes, inspect a narrow mobile viewport and a desktop viewport, keyboard focus, long text, and empty search results.
6. Submit a focused pull request describing the problem, behavior change, test evidence, and limitations.

Useful first contributions include framework fixture adapters, better contract error messages, accessibility improvements, and additional synthetic authorization cases. Discuss changes that add network access, arbitrary code execution surfaces, new evidence fields, or credential capture before implementation.

Avoid real personal data and external targets in tests. New verdicts require documented semantics. A passing report must never hide a failed setup, a server error, or a broken legitimate workflow. The contract and evidence formats are versioned; incompatible changes require a new schema version and migration guidance.

Contributions are licensed under Apache-2.0. Security reports follow [SECURITY.md](SECURITY.md).
