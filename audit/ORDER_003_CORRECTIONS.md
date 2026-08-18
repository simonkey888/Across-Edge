# ORDER-003 corrections

- C1: obsolete schema-v1/v2 tests retired/replaced; final evidence requires command/UTC/source HEAD/Python/platform/counts.
- C2: one-shot runtime replaced by nonzero canonical polling plus continuous observer supervisor, health/readiness, signals, bounded retry/restart and monotonic duration.
- C3: added `TA` live-equivalent confirmation gate; business metrics exclude early simulation-only T0.
- C4: winner reconciliation now uses canonical persisted chain order and works fill-before-shadow.
- C5: `FastFill=0` and `ReplacedSlowFill=1` compete; `SlowFill=2` excluded; unknown types mark evidence incomplete.
- C6: receive time captured before parse; direct indexed trace lookup; p50/p90/p99 benchmark added.
- C7: decode gaps persist/retry and block cursor certification.
- C8: reorg rollback restores chain-derived transitions/winners/cursors/gaps; equivalence test covers rewind+replay vs clean ingest.
- C9: final evidence index is rebuilt only after immutable ORDER-003 evidence is committed.
