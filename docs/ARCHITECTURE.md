# Architecture — ORDER-002

Across-Edge remains a wrapper around the exact canonical Across relayer pin. It does not reimplement relay correctness.

```text
canonical Across relayer @ 741ca9f7...
  Relayer.evaluateFill            -> T0 candidate enters canonical profitability path
  resolveRepaymentChain           -> T1 canonical decision/economics
  MultiCaller canonical simulate  -> T2 final simulation result
  TransactionClient.prepare       -> T3 unsigned populated/serialized transaction
  simulate=true                   -> RETURN BEFORE TransactionClient.submit
                 | stdout structured events only
                 v
Across-Edge coordinator -> SQLite v2 records -> independent RPC observer -> TW/first winner -> reports
```

The patch adds no signing or submission primitive. T3 calls only read-side population/serialization and runs inside the existing `simulate` branch before the canonical submit call. `SEND_RELAYS=false`, `SEND_TRANSACTIONS=false`, `--wallet void`, inventory/rebalance and registration-like execution flags are forced false.

Independent observation uses chain SpokePool logs, not relayer logs. Current target smoke route is Arbitrum One ↔ Base because both chains expose public no-auth RPCs and current Across SpokePool addresses are available from official sources.
