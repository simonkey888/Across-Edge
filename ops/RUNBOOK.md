# ORDER-003 runbook

## Preflight

1. Checkout Across-Edge branch `order-001-shadow-relayer` at the approved source HEAD.
2. Checkout `https://github.com/across-protocol/relayer` at the exact SHA in `config/upstream-pin.json`.
3. Apply `patches/across-relayer-order003-instrumentation.patch` and verify its SHA-256.
4. Run the full local gates in README.

## Sustained zero-spend shadow

```bash
python scripts/shadow_run.py ./upstream-relayer \
  --run-id order003-shadow \
  --duration 86400 \
  --polling-delay 5 \
  --observer-interval 2 \
  --export-interval 60
```

`POLLING_DELAY` must be positive. Ctrl-C or SIGTERM performs clean shutdown. Periodic artifacts and `health.json` are written under the selected output directory. SQLite WAL/cursors make observer restart safe.

Do not execute this command with any secret-bearing environment, non-void wallet, enabled send flag, paid endpoint, or funded signer.
