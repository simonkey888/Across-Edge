# Arbitrum sequencer-feed experiment

Reference pin: `nuntax/sequencer_client@96f5d856ec917e71f778cf726704d1049430d05f`, MIT per Amendment 001-A. Advertised reconnect/reordering/dedup/batch features remain upstream claims until reproduced; fixed batching/lead figures are not accepted as evidence.

Invariant: **feed = transactions, not executed logs**. Arbitrum-origin use can at most emit a pre-execution candidate from destination/calldata and must later reconcile against execution. Arbitrum-destination use may aid early winner observation.

`SEQUENCER_FEED_VERDICT=BLOCKED_BY_ZERO_COST_RUNTIME`. No Rust sidecar was promoted into the baseline.
