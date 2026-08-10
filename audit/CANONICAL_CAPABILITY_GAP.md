# Canonical capability-gap matrix — ORDER-001 / Amendment 001-A

Verified against Across relayer `741ca9f7d72923f7b13c1c2462ca90eba81e1a87` before substantial custom hot-path work.

| Requirement | Canonical feature | Exact file/function | Active for target route? | Sufficient? | Across-Edge delta | Decision |
|---|---|---|---|---|---|---|
| Transaction simulation | `TransactionClient.simulate()` / `_simulate()` -> `willSucceed()` | `src/clients/TransactionClient.ts` | Yes when relayer runs in simulation mode | Canonical correctness retained; exact T2 timing missing | timing hook + normalized result capture | WRAP |
| No-send shadow mode | `simulate = !sendingTransactionsEnabled || !sendingRelaysEnabled`; `SEND_RELAYS` false-by-default | `src/relayer/index.ts`, `RelayerConfig.ts` | Yes | Safe behavior exists, but ORDER-001 needs stronger outer fail-closed checks | reject keys/true send flags | WRAP |
| Void signer | CLI `--wallet void`; `VoidSigner(roAddress ?? AddressZero)` | `src/utils/CLIUtils.ts`, `SignerUtils.ts` | Yes | Yes for signer abstraction | pin exact CLI and validate arguments | REUSE |
| External/event listener | `RELAYER_EXTERNAL_LISTENER`; `RELAYER_EVENT_LISTENER`; SpokePool listener path | `RelayerConfig.ts`, `relayer/index.ts`, `SpokePoolClient.ts` | Conditional: looping + external listener | Runtime advantage unmeasured | benchmark before replacement | EXPERIMENT |
| Profiler | canonical `Profiler`, relayer loop timing via `performance.now()` | `src/relayer/index.ts`, `Relayer.ts` | Yes | Coarse spans only; no per-candidate T0-T3 contract | record-level monotonic hooks | WRAP |
| Multi-RPC spray | `AugmentedTransaction.spray` -> `getSpeedProvider()` | `TransactionClient.ts`, `ProviderUtils.ts` | `spray: true` search at pin found gasless utility, not canonical fill path | Not established for fills; live use prohibited | document only | REUSE/FUTURE |
| Redis/event cache | `getRedisCache`, provider cache, handover/inventory state | `cache/Redis.ts`, `ProviderUtils.ts`, `relayer/index.ts` | Optional | Useful but not required for local evidence | SQLite evidence store; retain upstream Redis semantics | WRAP |
| Inventory/rebalancing | `InventoryClient`; optional manager/CEX/fast-rebalance paths | `src/clients/InventoryClient.ts`, relayer config | Disabled for ORDER-001 | Financial execution out of scope | inspect/model only | REUSE/NO-EXEC |

No external broadcaster or local simulator is introduced by ORDER-001.
