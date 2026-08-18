# Across-Edge — ORDER-003

Zero-spend, read-only measurement harness for the canonical Across relayer. ORDER-003 completes the shadow software while preserving the absolute lock against live financial execution.

## Invariants

- exact upstream: `across-protocol/relayer@741ca9f7d72923f7b13c1c2462ca90eba81e1a87`
- exact instrumentation patch hash is bound in `config/upstream-pin.json`
- canonical process runs with `--wallet void`, `SEND_RELAYS=false`, nonzero `POLLING_DELAY`, and every auxiliary write path disabled
- observers use only allow-listed read JSON-RPC methods
- `T0` is raw observation; `TA` is first live-equivalent actionable observation under canonical minimum-confirmation logic
- business timing uses `TA`, never early simulation-only `T0`
- competitive winner types are `FastFill(0)` and `ReplacedSlowFill(1)`; `SlowFill(2)` is retained but excluded
- first winner is reconstructed from persisted `(blockNumber, logIndex, txHash, eventId)` order, independent of arrival order
- unresolved decode gaps make competitiveness evidence incomplete and hold the cursor behind the failing block

## Continuous command

```bash
python scripts/shadow_run.py ./upstream-relayer --duration 86400 --polling-delay 5 --observer-interval 2
```

The command verifies upstream identity/SHA and patch hash/applied state before starting. It supervises the no-send relayer, continuously polls origin/destination SpokePools, persists cursors, reconciles fills, exports periodic evidence, handles SIGTERM/SIGINT, and applies bounded restart/backoff to read-only components.

## Local gates

```bash
python -m pytest -q
python -m compileall -q src scripts
python scripts/secret_scan.py
python scripts/benchmark_coordinator.py --records 5000 --samples 1000
PYTHONPATH=src python -m across_edge.cli safety-check
```

Synthetic fixture results are never business evidence. `READY_BEFORE_WINNER` remains explicitly weaker than `WOULD_HAVE_WON`.

## ATM worker mode

`ACROSS_EDGE_ATM_WORKER_MODE` is additive and independent from relayer research. It accepts frozen read-only Web3 engineering jobs through `across-edge-worker`, operates only in isolated target checkouts, and has zero spend, signing, broadcast, write-RPC, claim, submission, payment or external-protocol-mutation authority. See `docs/ATM_WORKER_MODE.md`.
