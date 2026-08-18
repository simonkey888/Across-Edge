# ORDER-004 corrective closure checkpoint

Generated: 2026-08-10

## Remote truth

- repository: `simonkey888/Across-Edge`
- branch: `order-001-shadow-relayer`
- PR: `#2`, open, draft, unmerged
- `REMOTE_HEAD_SHA=5f5080b388246de26f74850565801b8f634ead14`
- `PR_HEAD_SHA=5f5080b388246de26f74850565801b8f634ead14`
- `MAIN_SHA=044d195f134178b6127af5dd3f5ad7d660d32e54`
- main unchanged: yes
- approved upstream pin: `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`

The previous ORDER-004 checkpoint described an older head. It is preserved. This document is the new correction checkpoint and is bound to the current remote head above.

## Corrective closure

1. Immutable run-scoped deposit snapshots were added. Global canonical deposit rows are no longer replaced by a later observation. Reports and reconciliation use the requested run's snapshots.
2. Canonical fill rows remain immutable, while run-scoped fill observations carry observation timestamps/version context. This prevents a second run from inheriting the first run's observation clock.
3. Reorg operations remain run-scoped and canonical counters derive from current canonical run state.
4. Evaluation attempts remain distinct and immutable across repeated T0 loops, with aggregate references to first-actionable, first-ready and current-decision attempts.
5. Deposit version identity uses canonical speed-up/update fields when available and conservative unique identities when provenance is incomplete.
6. Pinned speed-up provenance was documented from relayer SHA `741ca9f7d72923f7b13c1c2462ca90eba81e1a87` and `@across-protocol/sdk@4.4.18`.
7. Internal schema version is now explicitly authoritative at `4`; upstream event envelope version `3` is treated as a protocol boundary, not a competing internal schema.
8. Economics reporting preserves observed/derived fields, exposes repayment/LP/profitability distributions, and refuses fabricated rebalance-dependent values or tail percentiles when the sample is insufficient.
9. Adversarial regression coverage was expanded for the requested structural defects.

## Fresh execution boundary

The repository is not mounted in the current execution filesystem. Direct local access fails because DNS cannot resolve `github.com`:

`git ls-remote https://github.com/simonkey888/Across-Edge.git ...` → exit 128, `Could not resolve host: github.com`.

No paid GitHub Actions run was started. The current commit has no associated workflow runs. Therefore executable pytest/compileall/safety/secret-scan evidence cannot honestly be claimed from this environment. The new test source and structural changes are committed remotely, but execution remains `BLOCKED_VALID`.

No attempt was made to bypass the restriction with paid infrastructure, credentials, proxy/VPN, private RPC, wallet material, signing or broadcast.

## Evidence classification

- previous ORDER-003 59-test artifact: historical only;
- previous ORDER-004 checkpoint: historical/superseded for current-head claims, preserved intact;
- this checkpoint: current remote-state and structural-implementation evidence;
- fresh executable test result: blocked valid, not PASS;
- real-network evidence: blocked valid.

## Safety

`AUTHORIZED_SPEND_USD=0`
`PRIVATE_KEYS=0`
`TRANSACTIONS=0`
`ONCHAIN_VALUE_TRANSFER=0`
`MERGED=NO`
`MAIN_UNCHANGED=YES`
`UPSTREAM_PIN_UNCHANGED=YES`
`LIVE_FINANCIAL_EXECUTION=PROHIBITED`
