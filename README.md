# EvidenceClock

[![CI](https://github.com/BryanFiFife/EvidenceClock/actions/workflows/ci.yml/badge.svg)](https://github.com/BryanFiFife/EvidenceClock/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/runtime%20dependencies-0-success)
![License](https://img.shields.io/badge/license-MIT-blue)
![Freshness](https://img.shields.io/badge/evidence-transitive%20TTL-8A2BE2)
![Mode](https://img.shields.io/badge/checks-deterministic-informational)

**A decision cannot be fresher than its stalest prerequisite.**

EvidenceClock is a zero-dependency freshness and integrity primitive for autonomous agents. It represents evidence as a dependency graph, gives every observation a TTL, and propagates the earliest expiry transitively into the decisions built from it.

## Why this exists

Long-running agents pause, retry, wait for humans and resume from durable state. The plan may still be intact while the world it was based on has changed: inventory, policy, prices, permissions, files or external facts. A timestamp on the final answer is not enough. Freshness has to follow the **dependency chain**.

## Core rule

For node `N`:

```text
effective_expiry(N) = min(own_expiry(N), effective_expiry(each dependency))
```

If a five-hour decision depends on a five-minute inventory snapshot, the decision is five minutes fresh.

## Quick start

```bash
git clone https://github.com/BryanFiFife/EvidenceClock.git
cd EvidenceClock
PYTHONPATH=src python -m evidenceclock.cli verify examples/manifest.json \
  --at 2026-08-30T00:04:59Z --no-file-check
```

## File evidence

Capture a local artifact with an observation time, TTL and SHA-256 digest:

```bash
PYTHONPATH=src python -m evidenceclock.cli capture-file policy.json --id policy --ttl 3600
```

The verifier rejects modified or missing files and rejects symlink evidence by default.

## Manifest shape

```json
{
  "decision_id": "ship-release",
  "nodes": [
    {"id":"policy","observed_at":"2026-08-30T00:00:00Z","max_age_seconds":86400,"depends_on":[]},
    {"id":"inventory","observed_at":"2026-08-30T00:00:00Z","max_age_seconds":300,"depends_on":[]},
    {"id":"decision","observed_at":"2026-08-30T00:00:00Z","max_age_seconds":3600,"depends_on":["policy","inventory"]}
  ],
  "roots": ["decision"]
}
```

## Failure semantics

- `0`: roots are fresh and integrity checks pass.
- `2`: manifest is valid but one or more roots are stale.
- `3`: malformed manifest, invalid graph or verifier error.

Cycles and missing dependencies fail closed. Timestamps require timezone information. Future observations beyond the configured clock-skew allowance are stale rather than trusted.

## What EvidenceClock is not

It does not decide whether a source was truthful, whether a URL is reputable, or whether a remote system changed after collection. It proves a narrower property: **the decision's declared prerequisites are still inside their validity windows and local evidence bytes have not changed.**

## Tests

```bash
python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
```

The suite covers TTL boundaries, transitive expiry, hidden cycles, missing dependencies, hash tampering, file deletion, symlinks, clock skew, deterministic source propagation and CLI exit codes.

## License
MIT.
