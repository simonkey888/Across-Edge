# Upstream pin and instrumentation

Canonical repository: `across-protocol/relayer`.

Approved SHA: `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`.

`verify_upstream_checkout()` fails closed on repository identity or HEAD mismatch. `verify_patch()` fails closed on patch SHA mismatch. `scripts/shadow_run.py` also requires `git apply --reverse --check` to prove the expected patch is already applied before runtime.

ORDER-003 instrumentation is intentionally minimal: `Relayer.evaluateFill()` supplies raw T0, confirmation-actionable TA, T1 and canonical economics; `MultiCallerClient` supplies T2/T3; `TransactionClient.prepare()` only populates and serializes unsigned data. No submit/sign/send primitive is added.

At the audited pin, canonical `evaluateFill()` only returns for insufficient confirmations when live transaction sending is enabled. That is why ORDER-003 separately records the same `deposit.blockNumber <= maxBlockNumber` condition and excludes early no-send simulation from business competitiveness until TA.
