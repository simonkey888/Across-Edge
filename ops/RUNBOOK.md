# ORDER-002 runbook

## Preconditions

- Git, Node `>=22.18.0`, Yarn/Corepack and Python `>=3.11`.
- No real signer secret in environment/files.
- Network endpoints must be read-only-use approved and zero incremental cost.

## 1. Prepare exact upstream

```bash
git clone https://github.com/across-protocol/relayer.git ./runtime/across-relayer
git -C ./runtime/across-relayer checkout 741ca9f7d72923f7b13c1c2462ca90eba81e1a87
python scripts/apply_upstream_patch.py ./runtime/across-relayer --check-only
python scripts/apply_upstream_patch.py ./runtime/across-relayer
```

Install upstream dependencies using its lockfile. Do not configure exchange, KMS, paid RPC, private key or mnemonic.

## 2. Local gates

```bash
python -m pytest
python scripts/secret_scan.py
PYTHONPATH=src python -m across_edge.cli safety-check
```

## 3. Observer-only bounded smoke

```bash
PYTHONPATH=src python -m across_edge.cli observe evidence/smoke.sqlite smoke-001 --chains arbitrum,base --backfill 128
```

Only `eth_blockNumber`, `eth_getLogs` and `eth_getBlockByNumber` are used by this path.

## 4. Integrated canonical shadow run

```bash
python scripts/shadow_run.py ./runtime/across-relayer --db evidence/order002-shadow.sqlite --run-id order002-real-001 --out evidence/order002-real-001
```

The launcher verifies upstream identity/SHA and that the pinned patch is applied. It constructs a minimal child environment, forces all send/inventory/rebalance flags false, and invokes `yarn relay --wallet void`. It runs the independent observer separately and correlates canonical T0–T3 records with winner fills.

## 5. Shutdown

SIGTERM the wrapper. It terminates the relayer child, waits briefly, then escalates to kill only if needed. SQLite WAL preserves committed evidence.

## Sustained run

The exact same command can be supervised for 24–72h only on an already-available runtime verified to incur zero incremental charge. ORDER-002 provides no cloud provisioning automation.
