# Arbitrum sequencer-feed experiment

Official Arbitrum chain information publishes `wss://arb1-feed.arbitrum.io/feed`. The regular sequencer feed is transaction data, not executed EVM logs. It may identify an Arbitrum-origin Across call candidate before an RPC log, but every candidate must later reconcile to execution/receipt/event state.

Reference client pin: `nuntax/sequencer_client@96f5d856ec917e71f778cf726704d1049430d05f`; its license is MIT. Author claims about traffic batching or fixed latency advantage are not accepted as measurements.

This environment cannot resolve external network hosts, so no WebSocket sample can be measured here. Verdict for this checkpoint: `EXPLICITLY_BLOCKED_BY_EXECUTION_SANDBOX_NETWORK`. No feed result is promoted into baseline.
