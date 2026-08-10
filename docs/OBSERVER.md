# Independent winner observer

`RpcObserver` performs only allow-listed JSON-RPC reads: `eth_blockNumber`, `eth_getLogs` and `eth_getBlockByNumber` for the observer path. It filters the current Across SpokePool address for the official `FundsDeposited` and `FilledRelay` event topics, decodes protocol identifiers, and persists them before reconciliation.

Restart state is a `(scope, chain_id)` cursor containing next block and prior block hash. On mismatch, the observer rewinds a bounded reorg window, removes orphaned chain events and clears affected first-winner fields before replay. Duplicate event IDs are `(tx_hash, log_index)` and are idempotent. A later competing fill is retained for competitor evidence but never overwrites the first observed winner.

Exclusivity uses destination-chain time. A deposit first seen on its origin chain is left `other` until a destination-chain head timestamp is observed. At `destination_time <= exclusivityDeadline`, a non-matching exclusive relayer remains `exclusive_other`; only `deadline + 1` becomes `step_in`. Transitions are persisted and survive restart.
