# ORDER-002 corrective closure map

- F1: Added SHA-bound upstream instrumentation patch for canonical T0/T1/T2/T3, unsigned populated serialization at T3, coordinator parser, patch hash gate. Patch syntax and local contract tests pass; pinned upstream build/runtime is still externally blocked in this execution environment.
- F2: Added a real JSON-RPC `RpcObserver` using official event topics, current SpokePool addresses, bounded backfill, persistent cursors and read-only methods only.
- F3: Exact duplicate fill returns before winner mutation; later competing fills are stored but cannot replace first winner.
- F4: Classification uses destination time, inclusive exclusivity deadline, address/bytes32 normalization and persisted exclusive→step-in transitions.
- F5: Runtime verifies canonical remote identity and exact upstream SHA before launch; patch SHA is independently pinned.
- F6: Stage machine enforces strict order, monotonic time and no overwrite by default.
- F7: Expanded fail-closed safety flags, read-only RPC allowlist, void-signer gate, prohibited broadcaster and test matrix.
- F8: Secret scan covers tracked evidence and source; only one exact fixture path is allowlisted; findings print metadata only.
- F9: Sequential behavior is named `fallback_read`; true parallel read racing is separate and experimental.
- F10: Upstream patch captures canonical profitability USD components, LP fee pct and repayment chain; rebalance remains explicit `UNKNOWN` when unmeasured.
- F11: Run metadata includes exact SHAs, config fingerprint, schema, UTC + monotonic runtime, route set, redacted endpoint classes and fresh gate states.
- F12: Added exact pin/patch preparation and integrated `shadow_run.py` path; upstream remains external and subject to AGPL-3.0-only.
