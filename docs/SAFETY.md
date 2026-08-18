# Safety envelope

ORDER-003 inherits the absolute zero-spend lock:

- no private key, mnemonic, funded wallet, signer secret, exchange credential or cloud credential;
- upstream wallet must be `void`;
- `SEND_RELAYS`, `SEND_TRANSACTIONS`, slow-relay, inventory, executor, proposer, disputer, rebalance, swap, nomination and registration write flags must remain false;
- RPC allowlist excludes every send/personal/wallet write method;
- `ProhibitedBroadcaster` always raises;
- runtime environment is constructed from a narrow non-secret allowlist;
- URLs/logs are sanitized before persistence;
- secret scanner covers the committed surface with one explicit negative-test fixture exception.

`LIVE_EXECUTION_LOCK=PASS_STATIC / EXECUTION_NOT_TESTED` is the strongest valid claim when the patched upstream cannot be built/executed in the current environment. It must not be promoted to executable PASS without fresh upstream runtime evidence.
