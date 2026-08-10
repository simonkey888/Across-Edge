# Safety — ORDER-002

Hard invariant: zero spend, zero value transfer, zero live financial execution.

Runtime rejects secret signer material, any wallet other than `void`, any enabled relay/transaction/slow-relay/inventory/rebalancer/executor/registration/nomination flag, and every RPC method outside a read-only allowlist. `ProhibitedBroadcaster` always throws. The integrated runtime builds a minimal child environment rather than blindly forwarding the parent environment.

Logs/errors are sanitized: URL userinfo/query/fragment are removed and bearer/key-like values are redacted. The committed-surface secret scanner scans source, docs and evidence; it skips only binary suffixes and one exact negative-test fixture.

The upstream patch reaches T3 only from the existing canonical simulation branch and returns before `TransactionClient.submit`. The patch contract test rejects additions containing `eth_sendRawTransaction`, `.submit(` or `signTransaction(`.
