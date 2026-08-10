# Evidence index — ORDER-001 → ORDER-004 lineage

Current ORDER-004 source HEAD (last source commit before evidence-only commits): `5f5080b388246de26f74850565801b8f634ead14`.
Current branch evidence HEAD moves after each evidence-only commit; evidence artifacts explicitly bind their claims to the source HEAD above.

| Artifact / evidence family | Order | Status | Meaning |
|---|---:|---|---|
| `evidence/LOCAL_E2E_OUTPUT.txt`, `evidence/fixture-e2e/**` | 001 | SYNTHETIC | Fixture-only timing vectors; never business evidence. |
| `evidence/LOCAL_TESTS.txt`, `evidence/SAFETY_CHECK.txt`, `evidence/SECRET_SCAN.txt` | 001 | SUPERSEDED | Historical local checks. |
| `evidence/ORDER002_LOCAL_TESTS_FINAL.txt` | 002 | SUPERSEDED / NOT_VALID_FOR_FINAL_HEAD | Historical 34-test artifact. |
| `evidence/ORDER002_INSTRUMENTATION_BENCHMARK.json` | 002 | SUPERSEDED | Historical pre-TA/O(N) benchmark. |
| `evidence/ORDER002_RPC_ARBITRUM.*`, `evidence/ORDER002_RPC_BASE.*`, `evidence/ORDER002_SEQUENCER_FEED_DNS.json`, `evidence/ORDER002_UPSTREAM_ACQUIRE.*` | 002 | FAILED_ATTEMPT / BLOCKED | Historical network attempts. |
| `evidence/ORDER003_FINAL_TESTS.txt` | 003 | HISTORICAL_CURRENT_AT_ORDER003 | Valid only for source HEAD `c9c446d20a786b4066ffa1f473259d484cbab696`; never a current ORDER-004 test result. |
| `evidence/ORDER003_FINAL_VERIFICATION.json` | 003 | HISTORICAL_CURRENT_AT_ORDER003 | Preserved source-bound ORDER-003 metadata. |
| `evidence/ORDER003_NETWORK_ATTEMPT.json` | 003 | BLOCKED | Historical no-auth endpoint DNS attempt. |
| `evidence/ORDER003_UPSTREAM_RUNTIME_BLOCKER.json` | 003 | BLOCKED | Historical upstream acquisition blocker. |
| `evidence/ORDER004_STATIC_VERIFICATION.json` | 004 | SUPERSEDED / HISTORICAL | Previous static checkpoint; preserved and not relabeled for the current source head. |
| `evidence/ORDER004_TEST_STATUS.txt` | 004 | SUPERSEDED / HISTORICAL | Previous blocked test status; preserved. |
| `audit/ORDER_004_CLOSURE.md` | 004 | SUPERSEDED / HISTORICAL | Previous ORDER-004 checkpoint; preserved. |
| `audit/ORDER_004_CORRECTIVE_CLOSURE.md` | 004 | CURRENT_SOURCE_BOUND | Fresh corrective scope and execution boundary for source HEAD `5f5080b388246de26f74850565801b8f634ead14`. |
| `evidence/ORDER004_CORRECTIVE_VERIFICATION.json` | 004 | CURRENT_BLOCKED_VALID | Fresh source-bound corrective verification metadata; no execution PASS claimed. |
| `evidence/ORDER004_CORRECTIVE_TEST_STATUS.txt` | 004 | CURRENT_BLOCKED_VALID | Fresh test execution boundary; no stale PASS reused. |
| `evidence/ORDER004_NETWORK_ATTEMPT.txt` | 004 | CURRENT_BLOCKED_VALID | Fresh zero-cost network boundary. |
| `docs/UPSTREAM_SPEEDUP_PROVENANCE_ORDER004.md` | 004 | CURRENT_PROVENANCE | Pinned relayer/SDK speed-up field provenance. |
| `docs/SCHEMA_VERSIONING_ORDER004.md` | 004 | CURRENT_SCHEMA_POLICY | Current internal schema is 4; upstream event envelope is 3. |
| `patches/across-relayer-order003-instrumentation.patch` + `config/upstream-pin.json` | 004 | CURRENT_STATIC | Approved upstream pin and unchanged instrumentation patch. |
| real-network shadow records / real winners / real economics | 004 | NOT_AVAILABLE | No real-network sample exists in this environment. |

## Policy

`CURRENT_SOURCE_BOUND` means the artifact is bound to the current source head but may describe a blocked execution boundary. `CURRENT_BLOCKED_VALID` means a fresh execution attempt/limitation is recorded without converting it into PASS. Historical evidence is retained and never rewritten into current evidence.
