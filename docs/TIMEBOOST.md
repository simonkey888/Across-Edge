# Timeboost forensics — refreshed 2026-08-10

Current Offchain Labs Nitro configuration exposes Timeboost controls including an Express Lane auction contract/auctioneer, early-submission grace and an `express-lane-advantage` default of 200 ms in the published Nitro chart. This proves mechanism/configuration existence, not usage by any Across relayer.

No on-chain or feed evidence collected in this checkpoint can attribute an observed Across winning fill to the Express Lane. No auction bid, wallet, subscription, or transaction submission is authorized.

`TIMEBOOST_RELEVANCE=UNKNOWN`

Primary sources:
- OffchainLabs community Nitro chart: `https://github.com/OffchainLabs/community-helm-charts/blob/main/charts/nitro/README.md`
- Arbitrum chain information: `https://docs.arbitrum.io/for-devs/dev-tools-and-resources/chain-info`
