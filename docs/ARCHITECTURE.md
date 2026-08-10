# Architecture — ORDER-003

Across-Edge wraps rather than replaces canonical Across logic.

1. The pinned relayer emits version-3 instrumentation events from canonical `Relayer`, `MultiCallerClient`, and `TransactionClient` paths.
2. `ShadowCoordinator` captures a Python `perf_counter_ns()` receive mark before JSON parsing, performs an indexed `(run_id, trace_id)` lookup, and persists stages.
3. `RpcObserver` independently reads SpokePool deposits/fills, persists chain-order events and cursors, and records unresolved decode gaps.
4. `Observer.reconcile_deposit()` deterministically recomputes the winner from persisted chain order, so fill-before-shadow and overlap/replay are equivalent.
5. `ContinuousSupervisor` keeps the no-send relayer and read-only observers operating until shutdown, with bounded retry/restart and health/readiness state.
6. `reporting.py` exports deterministic evidence. Business metrics start at `TA`.

Clock boundary: Node `process.hrtime()` is stored only as source diagnostics. Cross-component durations use the Across-Edge process monotonic clock captured on receipt, including `TW` from observer threads in the same runtime.
