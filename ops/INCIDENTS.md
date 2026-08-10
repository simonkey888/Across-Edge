# Incident handling

- **Upstream SHA/repository mismatch:** stop; never repin silently.
- **Patch hash/apply mismatch:** stop; preserve diff/error metadata, no runtime.
- **Any secret detected:** stop; do not print the value; report only path/type/line and rotate externally if it was real.
- **Any send/inventory/rebalance flag true:** startup fails before child launch.
- **Reorg hash mismatch:** rewind bounded window, delete orphan chain evidence, clear affected winner attribution, replay.
- **Duplicate event:** ignore exact `(tx_hash, log_index)` replay; retain a distinct later competitor fill without replacing first winner.
- **RPC/DNS failure:** record sanitized endpoint class and failure; never substitute a paid endpoint automatically.
- **Unexpected exception:** sanitize before persistence/output; never dump environment.
