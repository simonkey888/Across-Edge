# RPC latency / hedged-read experiment

Upstream already has RetryProvider and `SpeedProvider`; live spray is prohibited. Across-Edge supplies a read-only JSON-RPC adapter and conservative fallback hedging. A real benchmark must record chain/runtime region, `eth_blockNumber`, `eth_getLogs`, relevant `eth_call`/`eth_estimateGas`, success/stale-head/timeout rates and p50/p90/p99.

`RPC_HEDGING_VERDICT=BLOCKED_BY_ZERO_COST_RUNTIME`: no endpoint was provisioned or assumed free. True parallel hedging must be justified by measured benefit. Write-side racing is prohibited.
