# Canonical capability-gap matrix — ORDER-001 / Amendment 001-A

Verified against Across relayer `741ca9f7d72923f7b13c1c2462ca90eba81e1a87` before substantial custom hot-path work.

| Requirement | Canonical feature | Exact file/function | Active? | Sufficient? | Across-Edge delta | Decision |
|---|---|---|---|---|---|---|
| Simulation | `TransactionClient.simulate/_simulate -> willSucceed` | `src/clients/TransactionClient.ts` | shadow mode | correctness yes; T2 timing missing | timing/result wrapper | WRAP |
| No-send shadow | `simulate = !sendingTransactionsEnabled || !sendingRelaysEnabled`; `SEND_RELAYS` true only on literal `true` | `src/relayer/index.ts`, `RelayerConfig.ts` | yes | canonical control exists | stronger outer fail-closed gate | WRAP |
| Void signer | `--wallet void` / `VoidSigner` | `src/utils/CLIUtils.ts`, `SignerUtils.ts` | yes | yes | pin/validate CLI | REUSE |
| Event listener | `RELAYER_EXTERNAL_LISTENER`, `RELAYER_EVENT_LISTENER`, SpokePool listener | `RelayerConfig.ts`, `relayer/index.ts`, `SpokePoolClient.ts` | conditional | route advantage unmeasured | benchmark before replacement | EXPERIMENT |
| Profiler | canonical `Profiler`, `performance.now()` | `relayer/index.ts`, `Relayer.ts` | yes | coarse only | per-candidate monotonic T0-T3 | WRAP |
| Multi-RPC spray | `AugmentedTransaction.spray -> getSpeedProvider()` | `TransactionClient.ts`, `ProviderUtils.ts` | fill use unproven | live prohibited | document only | REUSE/FUTURE |
| Redis/cache | Redis cache/provider cache/handover | `cache/Redis.ts`, `ProviderUtils.ts`, `relayer/index.ts` | optional | canonical where configured | local SQLite evidence only | WRAP |
| Inventory/rebalance | `InventoryClient` and optional manager/CEX paths | `InventoryClient.ts` | disabled here | financial execution out of scope | inspect/model only | REUSE/NO-EXEC |

Priority: REUSE canonical → WRAP thinly → MEASURE → EXPERIMENT if justified → BUILD last. No external broadcaster or local simulator is introduced.
