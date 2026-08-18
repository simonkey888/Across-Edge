# RPC latency / read racing

The prior function called “hedged” was sequential. ORDER-002 renames that behavior `fallback_read`.

A separate `parallel_read_race` issues the same **allow-listed read** concurrently and takes the first successful response; it is experimental and is not promoted into baseline until real measurements justify it. No write method can cross `JsonRpcClient`.

Verified public endpoints prepared for the target route:
- Arbitrum One: `https://arb1.arbitrum.io/rpc` (official Arbitrum docs; public, no SLA).
- Base: `https://mainnet.base.org` (official Base docs; free/rate-limited, not production-grade).
- Ethereum hub dependency: `https://ethereum-rpc.publicnode.com` (PublicNode's own public/free service page; optional runtime dependency for canonical hub state).

The current execution sandbox failed DNS resolution before the first `eth_blockNumber`; therefore real latency p50/p90/p99 is `EXPLICITLY_BLOCKED_BY_EXECUTION_SANDBOX_NETWORK`, not “blocked by cost.”
