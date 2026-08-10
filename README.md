# Across-Edge

ORDER-001 implementation: a production-oriented, **zero-spend, shadow-only** measurement layer around the canonical Across relayer. It answers whether a new relayer can observe eligible work, reach a fill-ready decision before the observed winner often enough to justify a later experiment — without risking capital now.

**LIVE FINANCIAL EXECUTION IS PROHIBITED.** No private key, mnemonic, registration, nomination write, exchange credential, paid endpoint, gas spend, bridge fill, transaction broadcast, or value transfer is part of ORDER-001.

Pinned canonical relayer: `across-protocol/relayer@741ca9f7d72923f7b13c1c2462ca90eba81e1a87` (AGPL-3.0-only). Upstream requires Node `>=22.18.0`; canonical CLI supports `--wallet void`; `SEND_RELAYS` is false unless explicitly set true. Across-Edge adds stronger fail-closed checks rather than relying on operator discipline.

Quickstart:

```bash
python -m pytest
python scripts/secret_scan.py
PYTHONPATH=src python -m across_edge.cli safety-check
```

Real-network observation is allowed only with endpoints/runtime already proven to have zero incremental cost. Sustained runtime is currently `BLOCKED_BY_ZERO_COST_RUNTIME`; the repository is deployment-ready but no paid/free-trial infrastructure was provisioned.

Important: **ready before winner is not equivalent to would have won**. Across-Edge reports headroom and observed competitor timing; it does not self-authorize a live test or claim financial viability.
