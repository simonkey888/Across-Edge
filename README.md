# Across-Edge

Across-Edge is a zero-spend, read-only research harness for measuring whether a new Across relayer can reach a canonical fill-ready decision before observed competitors without risking capital.

**ORDER-002 safety lock:** no funded wallet, no private key/mnemonic, no live relay, no transaction broadcast, no value transfer, no registration/nomination write, no swap/rebalance/CEX execution, no paid service provisioning. The canonical Across relayer runs only with `--wallet void`, `SEND_RELAYS=false` and `SEND_TRANSACTIONS=false`.

## What changed in ORDER-002

- exact upstream repository + SHA and instrumentation patch SHA fail closed;
- physical T0/T1/T2/T3 patch at canonical `Relayer` / `MultiCallerClient` / `TransactionClient` anchors;
- strict non-overwritable stage state machine;
- real read-only SpokePool observer with bounded backfill, cursor/restart and reorg rewind;
- duplicate replay idempotence and immutable first winner;
- destination-time exclusivity + persisted step-in transitions;
- full committed-surface secret scan and sanitized errors;
- canonical economics fields + explicit unknown rebalance cost;
- honest `fallback_read` vs isolated parallel read-race experiment;
- deterministic run metadata/reporting and integrated shadow runner.

## Local deterministic checks

```bash
python -m pip install --no-deps -e . pytest
python -m pytest
python scripts/secret_scan.py
PYTHONPATH=src python -m across_edge.cli safety-check
```

## Upstream preparation

```bash
git clone https://github.com/across-protocol/relayer.git /path/to/relayer
git -C /path/to/relayer checkout 741ca9f7d72923f7b13c1c2462ca90eba81e1a87
python scripts/apply_upstream_patch.py /path/to/relayer --check-only
python scripts/apply_upstream_patch.py /path/to/relayer
```

The script refuses a different repository identity, different SHA, or modified patch hash.

## Integrated shadow run

After installing the pinned upstream's dependencies at zero cost:

```bash
python scripts/shadow_run.py /path/to/relayer --run-id order002-real-001
```

The default prepared route is Arbitrum One → Base with public read-only endpoints, plus a public Ethereum RPC for canonical HubPool state. Current sandbox evidence records a DNS-resolution blocker before the first RPC read; it is not represented as an economic blocker or as real competitiveness data.

Synthetic fixture evidence from ORDER-001 remains historical test evidence only. `READY_BEFORE_WINNER` is never interpreted as `WOULD_HAVE_WON`.
