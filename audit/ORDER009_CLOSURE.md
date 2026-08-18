# ORDER-009 closure

Generated: 2026-08-15T02:32:52Z

## Source boundary

- Base before ORDER-009: `59f5988163449ef5c0866c3a4b9cf52d45032a66`
- Final source HEAD before this evidence-only commit: `3c770f755e199e3e6650a942c1fa8ccb51b7afc9`
- Main: `044d195f134178b6127af5dd3f5ad7d660d32e54` (unchanged)
- PR: `#2`, open, Draft, unmerged
- Upstream pin: `741ca9f7d72923f7b13c1c2462ca90eba81e1a87` (unchanged)
- Upstream current master observed at baseline: `5b03620f761aefb988c62131ddfd1d6e7146549c`

## Corrective source work

ORDER-009 repaired the two material TypeScript defects identified by AUD without changing architecture or the upstream pin:

1. `TransactionClient.prepare()` now builds an explicitly typed ethers-v5 `UnsignedTransaction`, converts nonce only after a fail-closed safe-integer bound, serializes without signing or sending, and has patched-upstream regression tests proving deterministic unsigned preparation and no sign/send calls.
2. `ProfitClient.isFillProfitable()` now exposes the already-computed canonical profitability economics as optional observed fields while preserving existing profitability behavior and leaving those values undefined when profitability computation fails. A patched-upstream regression test covers both cases.

The canonical patch also retains the prior T0/TA/T1/T2/T3, winner-observer, run-isolation, reorg and safety corrections. `tests/test_patch_contract.py` was strengthened for the new compile/runtime contract and mechanical hunk counts.

Final patch bytes are bound by SHA-256 `489e4a8c019c49a826bd01f9ac45d56fb739fbe39650833f13bed57544b382f8`; Git blob `6a354b6bdc84eb52789322736635f9eb4d0aa470`, size 20080 bytes.

## Execution attempts

A fresh exact-head harness `.github/workflows/order009-execution.yml` was added. Push at source HEAD `3c770f...` produced ORDER-009 run `31859270326`, job `94949586545`. GitHub allocated no runner (`runner_id=0`, `steps=[]`) and emitted the authoritative account-level annotation: the job was not started because recent account payments failed or the spending limit needs to be increased. No paid recovery was attempted.

The local ChatGPT sandbox also cannot clone the repository because DNS cannot resolve `github.com`. The connected GitHub integration returns HTTP 403 `Resource not accessible by integration` for the repository Codespaces API. Codex Process Jobs controller files and Codex-host Astral worker lanes are not exposed in this ChatGPT host. No other already-authorized zero-cost executable runtime is available to ARQ in this conversation.

Therefore fresh full pytest, compileall, secret scan, runtime safety, actual final-patch apply/typecheck/build/upstream tests, network and shadow gates could not be executed honestly. Historical PASS values were not reused.

## Final security gate

A bounded static Codex-Security-style review inspected the changed patch, `safety.py`, `upstream.py`, `shadow_run.py` and the ORDER-009 workflow. No material security regression was identified: production additions contain no sign/send/submit call, runtime remains `--wallet void`, send/write feature flags remain false/fail-closed, RPC is read-only allowlisted and loadable dotenv files are rejected. The dedicated independent Codex Security scanner/subagent is not available on this host, so this is `PASS_STATIC_BOUNDED`, not a substitute for the blocked fresh secret/runtime safety gates.

## Verdict

`ORDER_009_STATUS=BLOCKED_REAL` because the known source-level compile defects were corrected, but every executable zero-cost surface actually controllable by ARQ is blocked before a fresh checkout/run. This does not claim the new patch compiles; executable verification remains an explicit unknown pending an available zero-cost runner.

Safety remained: spend $0, private keys 0, signing 0, transactions 0, write RPC 0, on-chain value transfer 0, merge NO, main unchanged.
