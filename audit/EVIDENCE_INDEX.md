# Evidence index — ORDER-003 final lineage

Canonical source HEAD for ORDER-003 verification: `c9c446d20a786b4066ffa1f473259d484cbab696`.

| Artifact / evidence family | Order | Status | Meaning |
|---|---:|---|---|
| `evidence/LOCAL_E2E_OUTPUT.txt`, `evidence/fixture-e2e/**` | 001 | SYNTHETIC | Fixture-only timing vectors; never business evidence. |
| `evidence/LOCAL_TESTS.txt`, `evidence/SAFETY_CHECK.txt`, `evidence/SECRET_SCAN.txt` | 001 | SUPERSEDED | Historical local checks from ORDER-001. |
| `evidence/ORDER002_LOCAL_TESTS_FINAL.txt` | 002 | SUPERSEDED / NOT_VALID_FOR_FINAL_HEAD | Historical 34-test artifact; explicitly invalid as final ORDER-003 evidence. |
| `evidence/ORDER002_INSTRUMENTATION_BENCHMARK.json` | 002 | SUPERSEDED | Pre-TA/O(N)-era benchmark; retained for lineage only. |
| `evidence/ORDER002_RPC_ARBITRUM.*`, `evidence/ORDER002_RPC_BASE.*`, `evidence/ORDER002_SEQUENCER_FEED_DNS.json`, `evidence/ORDER002_UPSTREAM_ACQUIRE.*` | 002 | FAILED_ATTEMPT / BLOCKED | Historical DNS/network attempts; not current business data. |
| `evidence/ORDER003_FINAL_TESTS.txt` | 003 | CURRENT | Source-bound full-suite result with command, UTC, Python/platform and counts. |
| `evidence/ORDER003_FINAL_VERIFICATION.json` | 003 | CURRENT | Consolidated source-bound test/compile/secret/safety/benchmark/upstream-probe metadata. |
| `evidence/ORDER003_COORDINATOR_BENCHMARK.json` | 003 | CURRENT | Representative indexed receive→parse→SQLite benchmark; Node clock excluded. |
| `evidence/ORDER003_NETWORK_ATTEMPT.json` | 003 | BLOCKED | Fresh no-auth endpoint DNS probe from execution sandbox. No RPC response was obtained. |
| `evidence/ORDER003_UPSTREAM_RUNTIME_BLOCKER.json` | 003 | BLOCKED | Exact upstream acquisition/runtime blocker: execution sandbox cannot resolve GitHub. |
| `patches/across-relayer-order003-instrumentation.patch` + `config/upstream-pin.json` | 003 | CURRENT_STATIC | Exact patch/hash/source pin; patch apply/build/runtime remain externally unverified. |
| real-network shadow records / real winners / real economics | 003 | NOT_AVAILABLE | No real-network sample exists in this environment; all business metrics remain UNKNOWN. |

## Evidence policy

`CURRENT` means valid for the ORDER-003 source HEAD above. `SYNTHETIC` never supports competitiveness or economics. `BLOCKED` records a real attempted boundary, not a successful measurement. Historical artifacts are retained and never rewritten into current evidence.
