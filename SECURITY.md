# Security policy

Version 0.1 is an alpha research/developer tool. The bundled lab intentionally contains vulnerable behavior selected by `create_vulnerable_app`; the corrected factory is `create_fixed_app`. The lab is executed in-process by the CLI and is not a production service.

## Report a vulnerability

If the published repository has GitHub private vulnerability reporting enabled, use **Security → Report a vulnerability**. If it is unavailable, contact the maintainer through their GitHub profile to arrange a private channel before sending technical details. Do not post credentials, personal data, or sensitive findings in a public issue.

Include the affected version, synthetic reproduction, expected and actual behavior, impact, and any proposed fix. Response times are best effort; there is no commercial response SLA.

## Relevant trust boundaries

- Contracts cannot specify an importable factory or executable script. Application imports require an explicit CLI argument, except the two bundled factories.
- A custom factory is trusted Python code, not sandboxed code. ASGI in-process transport is not a process/container/VM isolation boundary.
- Evidence omits raw response content and resolved credentials, but includes the contract itself. Keep fixture data synthetic.
- Integrity checks are not signatures or authenticity attestations.
- Reports embed evidence as escaped JSON and use text-based rendering; report network connections are disabled by CSP.
- Automated request sequences are intended for owned, disposable test fixtures.

See [architecture](docs/architecture.md) for current limitations, including the absence of hard execution timeouts.
