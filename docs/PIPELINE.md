# Pipeline semantics

`T0` — raw canonical evaluation observation. Stores deposit block, current canonical `maxBlockNumber`, and whether the minimum-confirmation gate is satisfied.

`TA` — first observation that is live-equivalent actionable at the canonical minimum-confirmation gate. Early no-send simulation may continue internally, but it is labelled `SIMULATION_EARLY_NOT_LIVE_ACTIONABLE`; no T1/T2/T3 trace is attached before TA.

`T1` — canonical eligibility/profitability result after TA. Canonical fee/gas/net components are propagated where available; missing rebalance cost remains `UNKNOWN`.

`T2` — result of canonical `MultiCallerClient` simulation for a transaction carrying an actionable trace.

`T3` — unsigned populated/serialized transaction-ready state inside simulation mode, before any submit path. It never signs or broadcasts.

`TW` — earliest competitive fill selected by persisted chain order. `FastFill(0)` and `ReplacedSlowFill(1)` compete. `SlowFill(2)` and unknown future fill types do not enter winner/headroom metrics.

Business latency is `TA→T1→T2→T3`, and headroom compares T3 to TW only when both clocks are comparable and the winner is a competitive fill type.
