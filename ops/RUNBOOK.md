# ORDER-001 runbook

Prerequisites: Python 3.11+. Pinned upstream needs Node >=22.18.0. Redis is optional upstream for caching/state coordination; Across-Edge evidence uses SQLite.

1. `python -m pytest`
2. `python scripts/secret_scan.py`
3. `PYTHONPATH=src python -m across_edge.cli safety-check`
4. Clone upstream separately and checkout exactly `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`.
5. Supply only RPC/runtime already verified to have zero incremental charge; never commit key-bearing URLs.
6. Launch only with `SEND_RELAYS=false SEND_TRANSACTIONS=false yarn relay --wallet void --address 0x0000000000000000000000000000000000000000`.
7. Keep DB under `runs/`; export with `across-edge report <db> <run_id> artifacts/<run_id>`.

If free status cannot be proven, stop with `BLOCKED_BY_ZERO_COST_RUNTIME`.
