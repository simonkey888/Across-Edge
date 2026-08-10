# Canonical T0→T3 pipeline

Pinned upstream: `across-protocol/relayer@741ca9f7d72923f7b13c1c2462ca90eba81e1a87`.

| Stage | Exact canonical anchor | Meaning |
|---|---|---|
| T0 | `Relayer.evaluateFill`, immediately before `resolveRepaymentChain()` after structural/age gates | candidate reaches canonical profitability/repayment decision path |
| T1 | `Relayer.evaluateFill`, after `resolveRepaymentChain()` and canonical balance/overcommit gates | canonical eligibility/profitability decision complete; canonical economics captured when available |
| T2 | `MultiCallerClient._executeTxnQueue`, after batch/individual canonical simulation selects final transaction requests | final canonical simulation outcome |
| T3 | same `simulate` branch, `TransactionClient.prepare()` | unsigned transaction populated and serialized, broadcaster-ready but never submitted |

Across-Edge stamps its own `perf_counter_ns()` when each structured upstream event is received so T0–T3 durations use one monotonic clock domain. Upstream also emits `process.hrtime.bigint()` for source-side diagnostics, but cross-process duration math does not mix clocks.

Rejected T1 candidates intentionally do not receive T2/T3. The stage machine forbids T1 before T0, T2 before T1, T3 before T2, stage overwrite, and backwards monotonic timestamps.
