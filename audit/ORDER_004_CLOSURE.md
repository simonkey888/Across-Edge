# ORDER-004 structural closure

Source HEAD: `615a0d07b6c61a3cb26eafa04e602e004894facc`.

Implemented corrective scope:

- dotenv/config reinjection is fail-closed before the upstream child process starts; `.env` and `.env.*` are rejected, with `.env.example` explicitly allowed;
- repeated canonical evaluations have immutable `evaluation_attempt_id` records and explicit first-actionable, first-ready and current-decision references;
- deposit-version identity is deterministic when update provenance is present and conservative when update provenance is incomplete; unknown update provenance is never guessed;
- deposits, fills, cursors, attempts, transitions, decode gaps and derived aggregates are associated with `run_id`; reorg accepts an explicit run scope;
- canonical counters are derived from current run state and are separate from operational lifetime counters;
- reports query only the requested run's deposits/fills and expose canonical economic components already captured, while rebalance-dependent final values remain explicitly unknown;
- adversarial ORDER-004 regression tests cover all seven requested defect classes.

Safety remains unchanged: zero authorized spend, no keys, no signing, no broadcast, no value transfer, no paid runtime, no merge, no micro-live.

## Verification boundary

The current execution environment cannot resolve `github.com`, so a fresh checkout of the repository cannot be executed locally and no paid CI was started. The prior ORDER-003 `59 PASS` artifact is retained only as historical evidence and is not relabeled as ORDER-004 verification.

The exact approved upstream master remains `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`. No upstream pin change was made.
