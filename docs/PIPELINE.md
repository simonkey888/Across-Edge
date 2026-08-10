# Canonical pipeline map

Pin: `across-protocol/relayer@741ca9f7d72923f7b13c1c2462ca90eba81e1a87`.

`runRelayer()` constructs clients, updates them, then calls `checkForUnfilledDepositsAndFill(simulate)`. `simulate` is true whenever global transaction sending or relay sending is disabled. SpokePool updates include `FundsDeposited`, `RequestedSpeedUpDeposit`, `FilledRelay`, `RelayedRootBundle`, and `ExecutedRelayerRefundRoot`.

- T0: earliest trusted actionable candidate seen by the canonical event/log path. Sequencer-feed pre-execution observation is separately named and is not an executed log.
- T1: canonical route/exclusivity/token/confirmation/profitability eligibility decision complete in `Relayer`.
- T2: canonical `TransactionClient.simulate()` → `_simulate()` → `willSucceed()` complete.
- T3: exact candidate fill transaction populated/serialized and broadcaster-ready; ORDER-001 broadcaster remains prohibited.
- TW: independently observed destination `FilledRelay` winner.
- HEADROOM = TW − T3 using monotonic timestamps only.

Potential round trips include SpokePool events, ConfigStore/HubPool/token state, limits API where enabled, price/gas inputs, simulation RPC, and optional Redis. Counts vary by route/cache state and must be measured rather than hard-coded. Current event names are `FundsDeposited` and `FilledRelay`.
