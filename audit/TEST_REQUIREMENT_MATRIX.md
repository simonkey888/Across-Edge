# ORDER-002 test-to-requirement matrix

| Requirement | Evidence/test |
|---|---|
| strict T0→T1→T2→T3, no skip/overwrite/backwards | `tests/test_instrumentation.py` |
| canonical event correlation | `tests/test_coordinator.py` |
| exact duplicate fill replay idempotence / first winner immutable | `tests/test_observer_replay.py` |
| deadline-1 / deadline / deadline+1 + address↔bytes32 | `tests/test_classification.py` |
| exclusive→step-in transition persisted across restart | `tests/test_observer_replay.py` |
| reorg rewind removes orphan fill and clears winner | `tests/test_storage_reorg.py` |
| upstream repository + exact SHA fail closed | `tests/test_upstream_pin.py` |
| keys / non-void signer / send flags / broadcaster / write RPC fail closed | `tests/test_safety.py` |
| URL/log sanitization | `tests/test_safety.py`, `tests/test_runmeta.py` |
| sequential fallback honestly named + parallel read race isolated | `tests/test_rpc.py` |
| canonical USD unit normalization + explicit rebalance UNKNOWN | `tests/test_profitability.py` |
| official event topic derivation | `tests/test_evm_topics.py` |
| instrumentation patch contains T0-T3 and adds no signing/send primitive | `tests/test_patch_contract.py` |
| full committed surface secret scan | `scripts/secret_scan.py` |

The matrix proves local deterministic behavior. It does **not** claim the TypeScript patch compiled or ran inside the pinned upstream checkout; that requires the external upstream runtime evidence gate.
