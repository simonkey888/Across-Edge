# CHAIN_RPC_BOUNDARY

ATM worker protocol access is read-only.

A job must bind every allowed chain ID and every HTTPS endpoint. URL credentials, query strings, non-HTTPS endpoints and undeclared chains are rejected. `ReadOnlyRpcClient` rejects redirects/final-host changes and admits only the read-method allowlist inherited from `across_edge.safety.assert_read_only_rpc_method`.

Before accepting evidence, the client verifies `eth_chainId` against the frozen chain ID and reads a latest block. Evidence binds:

- chain ID;
- sanitized endpoint;
- JSON-RPC method;
- block number;
- block hash;
- observation timestamp;
- response SHA-256.

Write/send/personal/wallet RPC methods fail closed. Unsigned transactions are data structures only; signature fields and secret material are rejected and no broadcast path exists in worker mode.
