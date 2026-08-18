# ORDER-010 zero-write shadow operations

Canonical launcher: `python3 scripts/start_shadow.py <PINNED_UPSTREAM_CHECKOUT> --source-head <FINAL_PR_HEAD>`.

Status: `python3 scripts/status_shadow.py`.
Ensure/recover: `python3 scripts/ensure_shadow.py <PINNED_UPSTREAM_CHECKOUT> --source-head <FINAL_PR_HEAD>`.
Stop: `python3 scripts/stop_shadow.py`.

The launcher uses the pinned upstream, SHA-bound runtime patch, direct `node ./dist/index.js --relayer`, local bounded Redis, public no-key RPC defaults, a valid empty local address list plus upstream remote risk list, void wallet, and all send/write paths disabled.
