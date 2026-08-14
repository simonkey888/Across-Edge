# Evidence index — ORDER-001 → ORDER-008 lineage

Current ORDER-008 corrective source HEAD: `157a21f82c7172dea267b239a8accb7fd289ed06`.
Current `main`: `044d195f134178b6127af5dd3f5ad7d660d32e54`.
Approved upstream pin: `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`.

| Artifact / evidence family | Order | Status | Meaning |
|---|---:|---|---|
| `evidence/LOCAL_E2E_OUTPUT.txt`, `evidence/fixture-e2e/**` | 001 | SYNTHETIC | Fixture-only timing vectors; never business evidence. |
| `evidence/LOCAL_TESTS.txt`, `evidence/SAFETY_CHECK.txt`, `evidence/SECRET_SCAN.txt` | 001 | SUPERSEDED | Historical local checks. |
| `evidence/ORDER002_LOCAL_TESTS_FINAL.txt` | 002 | SUPERSEDED / NOT_VALID_FOR_FINAL_HEAD | Historical 34-test artifact. |
| `evidence/ORDER002_INSTRUMENTATION_BENCHMARK.json` | 002 | SUPERSEDED | Historical pre-TA/O(N) benchmark. |
| `evidence/ORDER002_RPC_ARBITRUM.*`, `evidence/ORDER002_RPC_BASE.*`, `evidence/ORDER002_SEQUENCER_FEED_DNS.json`, `evidence/ORDER002_UPSTREAM_ACQUIRE.*` | 002 | FAILED_ATTEMPT / BLOCKED | Historical network attempts. |
| `evidence/ORDER003_FINAL_TESTS.txt` | 003 | HISTORICAL_CURRENT_AT_ORDER003 | Valid only for source HEAD `c9c446d20a786b4066ffa1f473259d484cbab696`; never reused as later-order execution evidence. |
| `evidence/ORDER003_FINAL_VERIFICATION.json` | 003 | HISTORICAL_CURRENT_AT_ORDER003 | Preserved source-bound ORDER-003 metadata. |
| `evidence/ORDER003_NETWORK_ATTEMPT.json` | 003 | BLOCKED | Historical no-auth endpoint DNS attempt. |
| `evidence/ORDER003_UPSTREAM_RUNTIME_BLOCKER.json` | 003 | BLOCKED | Historical upstream acquisition blocker. |
| `evidence/ORDER004_STATIC_VERIFICATION.json` | 004 | SUPERSEDED / HISTORICAL | Previous static checkpoint; preserved. |
| `evidence/ORDER004_TEST_STATUS.txt` | 004 | SUPERSEDED / HISTORICAL | Previous blocked test status; preserved. |
| `audit/ORDER_004_CLOSURE.md` | 004 | SUPERSEDED / HISTORICAL | Previous ORDER-004 checkpoint; preserved. |
| `audit/ORDER_004_CORRECTIVE_CLOSURE.md` | 004 | HISTORICAL_SOURCE_BOUND | Corrective scope for source HEAD `5f5080b388246de26f74850565801b8f634ead14`. |
| `evidence/ORDER004_CORRECTIVE_VERIFICATION.json` | 004 | HISTORICAL_BLOCKED_VALID | Preserved source-bound corrective verification metadata; no execution PASS. |
| `evidence/ORDER004_CORRECTIVE_TEST_STATUS.txt` | 004 | HISTORICAL_BLOCKED_VALID | Preserved corrective test boundary; no stale PASS reused. |
| `evidence/ORDER004_NETWORK_ATTEMPT.txt` | 004 | HISTORICAL_BLOCKED_VALID | Preserved network boundary. |
| `docs/UPSTREAM_SPEEDUP_PROVENANCE_ORDER004.md` | 004 | CURRENT_SOURCE_DOCUMENTATION | Pinned relayer/SDK speed-up field provenance. |
| `docs/SCHEMA_VERSIONING_ORDER004.md` | 004 | CURRENT_SOURCE_DOCUMENTATION | Current internal schema is 4; upstream event envelope is 3. |
| `evidence/ORDER005_FINAL_VERIFICATION.json` | 005 | HISTORICAL_BLOCKED_VALID | ORDER-005 reconciliation/execution-boundary metadata. No execution PASS claimed. |
| `evidence/ORDER005_TEST_STATUS.txt` | 005 | HISTORICAL_BLOCKED_VALID | ORDER-005 test boundary; no stale PASS reused. |
| `evidence/ORDER005_NETWORK_ATTEMPT.txt` | 005 | HISTORICAL_BLOCKED_VALID | ORDER-005 zero-cost network acquisition attempt. |
| `audit/ORDER005_CLOSURE.md` | 005 | HISTORICAL | ORDER-005 execution-boundary checkpoint. |
| `.github/workflows/order006-execution.yml` | 006 | HISTORICAL_EXECUTION_HARNESS | GitHub Actions harness; runner start was billing/spending-limit blocked. |
| `evidence/ORDER006_FINAL/**` | 006 | HISTORICAL_BLOCKED_VALID | ORDER-006 evidence; Actions did not execute software. |
| `audit/ORDER006_CLOSURE.md` | 006 | HISTORICAL | ORDER-006 checkpoint. |
| `.github/workflows/order007-execution.yml` | 007 | HISTORICAL_EXECUTION_HARNESS | Push/dispatch harness; Actions continues to fail before runner allocation. |
| `evidence/ORDER007_FINAL/ORDER007_EXECUTION_STATUS.txt` | 007 | HISTORICAL_BLOCKED_VALID | ORDER-007 zero-cost execution-path status. |
| `audit/ORDER007_CLOSURE.md` | 007 | HISTORICAL | ORDER-007 checkpoint. |
| AUD Issue #7 comment `5288891689` | 008 | FRESH_CODESPACES_FAILURE_AT_D997 | Fresh Codespaces execution at `d997b13...`: compile/secret/safety passed; pytest exposed seven actionable failures; upstream runtime failed; network/shadow were not reached. |
| corrective commits `d997b13...` → `157a21f...` | 008 | CURRENT_SOURCE | Minimal fixes for repeated T0 identity, run-local fills, reorg restoration, fixtures, patch structure/hash and global winner reconciliation. |
| `patches/across-relayer-order003-instrumentation.patch` | 008 | CURRENT_STATIC | Corrected patch hunk structure for the unchanged upstream pin. |
| `config/upstream-pin.json` | 008 | CURRENT_STATIC | Upstream SHA unchanged; instrumentation patch SHA-256 is `8cf71677303d75a178f5a9a79c0a3127935afcf753623668b55a5535fe25ce19`. |
| `evidence/ORDER008_FINAL/ORDER008_CORRECTIVE_VERIFICATION.json` | 008 | CURRENT_BLOCKED_VALID | Source-bound post-correction status for `157a21f...`; explicitly no post-correction PASS claimed. |
| `evidence/ORDER008_FINAL/ORDER008_EXECUTION_BLOCKER.txt` | 008 | CURRENT_BLOCKED_VALID | Codespaces create/start is unavailable through the connected integration; repository Codespaces API returns 403. Latest Actions run also fails before runner start. |
| `audit/ORDER008_CORRECTIVE_CLOSURE.md` | 008 | CURRENT | Corrective checkpoint and exact remaining execution boundary. |
| real-network ORDER-008 shadow records / winners / economics | 008 | NOT_AVAILABLE | Post-correction execution has not reached network/shadow gates. |

## Policy

`CURRENT` / `CURRENT_BLOCKED_VALID` means the artifact belongs to the active ORDER-008 lineage and does not upgrade blocked execution into PASS. `CURRENT_SOURCE` identifies the exact corrected code lineage. `STATIC` means source/patch inspection only. `HISTORICAL` preserves prior evidence and is never reused as current execution evidence. `SYNTHETIC` never supports competitiveness or economics. Historical evidence is retained and never rewritten into a false current PASS.
