# Architecture

Across-Edge does not reimplement the Across relayer. The official pinned relayer remains the correctness engine. Across-Edge adds fail-closed launch controls, record-level T0–T3 timing, an independent read-only EVM event observer, SQLite evidence storage, competitor timing, P&L/break-even normalization, and isolated latency experiments.

```text
canonical Across relayer (SEND_RELAYS=false, SEND_TRANSACTIONS=false, --wallet void)
        | candidate / canonical decision / simulation / populated tx evidence
        v
Across-Edge safety + monotonic T0-T3 records
        |                         \
        |                          read-only eth_getLogs observer
        v                           \
SQLite WAL store <---------------- FundsDeposited / FilledRelay
        |
        +--> winner correlation / competitor scoreboard
        +--> shadow economics / break-even
        +--> JSONL/CSV/report artifacts
```

The RPC adapter allow-lists read methods; any `eth_send*` is rejected before I/O. `ProhibitedBroadcaster` always throws. Deposits and fill transaction hashes provide restart-safe deduplication.
