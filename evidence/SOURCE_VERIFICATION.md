# Source verification snapshot — 2026-08-09/10 UTC

Primary-source verification before implementation:
- Across relayer pin `741ca9f7d72923f7b13c1c2462ca90eba81e1a87`.
- package: Node `>=22.18.0`, AGPL-3.0-only, relay entrypoint.
- CLI/Signer: canonical `--wallet void` / `VoidSigner`.
- RelayerConfig: `SEND_RELAYS === "true"`; external/event listeners present.
- relayer/index: simulation when send controls disabled; Profiler/event-listener path present.
- TransactionClient: `simulate/_simulate/willSucceed`; `spray` reconnects through `getSpeedProvider`.
- ProviderUtils: `getSpeedProvider` races configured RPC endpoints.
- Pinned search found `spray: true` in gasless utility, not proof canonical fills use it.
- contracts interface pin `c959c80e6fbcce9a4b8e4b1321c70b0872297fa5`: `FundsDeposited` / `FilledRelay`.
- nuntax pin `96f5d856ec917e71f778cf726704d1049430d05f`; MIT per Amendment 001-A.
- Nitro source/config exposes Timeboost 200 ms express-lane advantage; specific Across-winner attribution not proven.
