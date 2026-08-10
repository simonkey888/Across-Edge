# Read-only observer

Each `RpcObserver` scans a SpokePool with bounded backfill and a restart-safe SQLite cursor. Event receive monotonic time is captured before ABI decoding/storage.

Decode failure policy is fail-closed for evidence completeness: the event is recorded as a sanitized unresolved gap with retry count; the certified cursor remains before the earliest failed block; later cycles retry from that block. Successful recovery marks the gap resolved.

Fill reconciliation is arrival-order-independent. All fills are retained; exact duplicates are idempotent; competitive winner selection uses persisted `(block_number, log_index, tx_hash, event_id)` ordering. Fill-before-shadow is reconciled when a shadow record later appears.

Reorg rewind removes orphan chain events and their derived state, rolls candidate transition history back to the latest surviving state, clears affected winners/cursors/gaps, and replay deterministically rebuilds canonical state.
