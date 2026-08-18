# Future live phase — design only

A later AUD order would need explicit capital and transaction authorization. Proposed controls: isolated minimum-balance hot wallet, per-fill notional cap, daily loss cap, route/token allow-list, minimum expected net margin, maximum gas, stale-data cutoff, nonce lock, duplicate-fill guard, circuit breaker on simulation mismatch/RPC divergence, and owner kill switch.

ORDER-001 creates/funds none of these.
