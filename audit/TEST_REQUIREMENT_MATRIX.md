# ORDER-003 test requirement matrix

| Requirement | Evidence test |
|---|---|
| Strict T0→TA→T1→T2→T3 | `test_instrumentation.py` |
| Confirmation insufficient/exact threshold/zero-confirm/restart | `test_coordinator_actionable.py` |
| Fill before shadow / restart | `test_reconciliation.py` |
| Two-fill canonical ordering | `test_reconciliation.py` |
| Duplicate overlap idempotence | `test_reconciliation.py` |
| Reorg reveals replacement winner | `test_reconciliation.py` |
| Fast/ReplacedSlow compete; Slow/unknown isolated | `test_fill_types.py` |
| Receive timestamp precedes parse; indexed direct lookup | `test_coordinator_actionable.py`, `test_direct_lookup_benchmark.py` |
| Decode gap blocks cursor and recovers | `test_decode_gap.py` |
| Reorg+replay equivalent to clean ingest | `test_storage_reorg_equivalence.py` |
| Continuous multi-cycle runtime / restart continuity / child restart | `test_supervisor.py` |
| Non-void wallet, secrets, write RPCs, execution flags blocked | `test_safety.py` |
| Upstream identity/SHA fail closed | `test_upstream_pin.py` |
| Instrumentation patch contains no send/sign additions | `test_patch_contract.py` |
| Unknowns not converted to zero/profit | `test_reporting.py`, `test_profitability.py` |
