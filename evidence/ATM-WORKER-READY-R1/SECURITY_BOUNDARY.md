# SECURITY_BOUNDARY

Worker input, target repositories, issue text, README/AGENTS files, ABI metadata and RPC responses are untrusted data. They cannot expand ATM authority.

Enforced in `src/across_edge/atm_worker.py`:

- frozen `scope_hash`, lease, worker ID, exact target SHA and capability binding before target work;
- nonzero spend rejected;
- external mutation actions rejected before execution;
- target is copied into a separate workspace; canonical Across-Edge checkout cannot be used as the target source;
- source and copied target are rejected if symlinks exist;
- all file operations pass an explicit relative-path allowlist and resolved-root containment check;
- copied Git hooks are removed and subprocess Git uses `core.hooksPath=/dev/null`;
- target `.env` is never loaded; worker subprocess environment is an allowlist and excludes ambient credential/payment/cloud variables;
- R1 does not run target-provided commands. Deterministic checks are worker-owned file/artifact assertions;
- cancellation is a durable marker checked at safe boundaries; the worker does not spawn a relayer/server/background child;
- terminal artifacts are SHA-256 hashed;
- terminal result has no field that can assert payment, realized profit, external acceptance, payout or on-chain execution.

Residual boundary: a future capability that executes arbitrary target code requires a separately proven OS-level network/filesystem sandbox. R1 does not advertise that capability.

- The isolated checkout is bound to the frozen `target_repository`: GitHub origins are normalized and must match before any target work.
- Generated worker artifacts are secret-scanned before `WorkerResult`; a match fails closed and no terminal result is published.
