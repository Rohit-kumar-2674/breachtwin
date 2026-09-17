# Architecture and trust boundaries

The 0.1 runtime has five layers:

| Layer | Inputs and responsibility |
| --- | --- |
| Contract validator | Validates versioned JSON, known actors, paths, probes, and required controls. No application imports. |
| Runner | Imports an explicitly supplied local factory, constructs a fresh app per experiment, enters ASGI lifespan, sends requests, and evaluates predicates. |
| Evidence builder | Records contract, outcomes, request metadata, runtime versions, factory reference, factory-module checksum, and duration. |
| Reporter | Embeds evidence into a self-contained HTML viewer with script-safe JSON and text-based DOM rendering. |
| Regression exporter | Emits a unittest that runs the contract and fails on every reproduced or inconclusive case. |

## What is isolated

Bundled app state is fresh per experiment. Requests use an ASGI in-process transport, so the demo has no exposed vulnerable service and makes no outbound HTTP requests. Actor headers are selected per step, and automatic cookie persistence is cleared between requests. Startup and shutdown hooks run for each factory instance.

**An in-process fixture is not an OS sandbox.** A custom factory is unrestricted trusted Python code and may access files, environment variables, databases, and networks. Its dependencies may also perform external operations. The tool makes no claim to contain hostile applications. Use a disposable environment for anything you do not fully control. The current release does not provide a hard timeout for a blocked factory or request.

The `view` command serves one existing report, binds only to `127.0.0.1`, checks the Host header, and rejects unrelated paths. It exposes no run, upload, import, shell, or filesystem-browsing API. Static reports use an embedded Content Security Policy that disallows network connections and external scripts, and all dynamic labels render as text.

## Evidence envelope

```json
{
  "format": "breachtwin.evidence",
  "schema_version": 1,
  "payload": {
    "run_id": "generated identifier",
    "factory": "explicit.module:factory",
    "contract": {},
    "environment": {},
    "results": [],
    "summary": {}
  },
  "integrity": {"algorithm": "sha256", "digest": "canonical payload checksum"}
}
```

The actual payload also includes timestamps, run label, duration, and scope. The checksum covers sorted-key, compact UTF-8 JSON with non-finite floats rejected. A modified payload fails verification unless its checksum is recomputed. Consequently, **this is integrity checking, not digital signing, trusted attestation, or forensic chain of custody**. Verify results by rerunning the experiment in a trusted environment.

Factory provenance is limited to the factory's Python module file. Its checksum does not cover all imports, the complete repository, data stores, operating-system libraries, or external services. Runtime package versions are recorded; the evidence bundle does not carry an executable container or dependency wheels. For stronger reproducibility, retain the source revision and install the included tested dependency snapshot. Elapsed time and run identifiers naturally differ on replay.

Contract predicates are the source of truth. Incorrect expected behavior can produce incorrect conclusions. “Blocked” describes only tested outcomes with passing controls, not universal safety. Reproduced cases are concrete contract violations in the selected fixture, not independently confirmed production vulnerabilities.

## Data handling

The runner does not serialize resolved environment credentials, raw response bodies, response headers, or exception messages. It does serialize the entire contract, including fixture bodies and expected values. Keep contracts synthetic and review exported evidence before sharing. No telemetry or AI service is implemented.

## Deliberate release limits

- FastAPI/local ASGI factories only; no live target URL mode.
- Explicit request sequences; no crawling, fuzzing, automatic vulnerability discovery, or natural-language policy inference.
- Bundled corrected implementations; no automated patch generation.
- JSON response predicates; no browser authentication or binary response inspection.
- No automatic per-actor session capture, multi-service orchestration, cloud replicas, or whole-program isolation.
- Human-authored fixes and contracts remain subject to review.
