# Evidence index — ORDER-001 → ORDER-004 lineage

Canonical ORDER-004 source HEAD: `615a0d07b6c61a3cb26eafa04e602e004894facc`.

| Artifact / evidence family | Order | Status | Meaning |
|---|---:|---|---|
| `evidence/LOCAL_E2E_OUTPUT.txt`, `evidence/fixture-e2e/**` | 001 | SYNTHETIC | Fixture-only timing vectors; never business evidence. |
| `evidence/LOCAL_TESTS.txt`, `evidence/SAFETY_CHECK.txt`, `evidence/SECRET_SCAN.txt` | 001 | SUPERSEDED | Historical local checks. |
| `evidence/ORDER002_LOCAL_TESTS_FINAL.txt` | 002 | SUPERSEDED / NOT_VALID_FOR_FINAL_HEAD | Historical 34-test artifact. |
| `evidence/ORDER002_INSTRUMENTATION_BENCHMARK.json` | 002 | SUPERSEDED | Historical pre-TA/O(N) benchmark. |
| `evidence/ORDER002_RPC_ARBITRUM.*`, `evidence/ORDER002_RPC_BASE.*`, `evidence/ORDER002_SEQUENCER_FEED_DNS.json`, `evidence/ORDER002_UPSTREAM_ACQUIRE.*` | 002 | FAILED_ATTEMPT / BLOCKED | Historical network attempts. |
| `evidence/ORDER003_FINAL_TESTS.txt` | 003 | HISTORICAL_CURRENT_AT_ORDER003 | Valid only for source HEAD `c9c446d20a786b4066ffa1f473259d484cbab696`; never a current ORDER-004 test result. |
| `evidence/ORDER003_FINAL_VERIFICATION.json` | 003 | HISTORICAL_CURRENT_AT_ORDER003 | Preserved source-bound ORDER-003 metadata. |
| `evidence/ORDER003_NETWORK_ATTEMPT.json` | 003 | BLOCKED | Fresh-at-the-time no-auth endpoint DNS attempt. |
| `evidence/ORDER003_UPSTREAM_RUNTIME_BLOCKER.json` | 003 | BLOCKED | Exact upstream acquisition blocker. |
| `evidence/ORDER004_STATIC_VERIFICATION.json` | 004 | CURRENT_STATIC | Current source-bound structural implementation checkpoint. |
| `evidence/ORDER004_TEST_STATUS.txt` | 004 | CURRENT_BLOCKED | Fresh test execution not performed because network/checkout is unavailable and paid CI is not authorized. |
| `audit/ORDER_004_CLOSURE.md` | 004 | CURRENT | Corrective scope and verification boundary. |
| `patches/across-relayer-order003-instrumentation.patch` + `config/upstream-pin.json` | 004 | CURRENT_STATIC | Approved upstream pin and unchanged instrumentation patch hash. |
| real-network shadow records / real winners / real economics | 004 | NOT_AVAILABLE | No real-network sample exists in this environment. |

## Policy

`CURRENT_STATIC` means current remote source/evidence state was inspected but executable verification is not claimed. `CURRENT_BLOCKED` means the missing gate was attempted/assessed and is externally unavailable. `SYNTHETIC` never supports competitiveness or economics. Historical evidence is retained and never rewritten into current evidence.
