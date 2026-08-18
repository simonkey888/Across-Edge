# Across-Edge modes

`ACROSS_EDGE_RESEARCH_MODE` is the standalone relayer/shadow-research project path. It may evolve under its own orders and does not depend on ATM.

`ACROSS_EDGE_ATM_WORKER_MODE` is an additive, isolated read-only engineering adapter. It has zero financial, claim, submission, model, protocol-mutation, signing, broadcast, funded-wallet or write-RPC authority. Its machine entrypoint is `across-edge-worker run --job <json> --state-dir <dir> --output-dir <dir>`.

The worker may read explicitly allowlisted public chain endpoints, inspect isolated target checkouts, apply bounded local source repairs inside those target checkouts, run worker-owned deterministic checks, and return content-hashed evidence. It cannot mutate Across-Edge's canonical checkout or relayer deployment/governance state. It cannot interpret a worker result as ATM acceptance, payment, payout, realized profit or on-chain execution.

Every job must hold an `ACTIVE`, unexpired frozen lease and `max_spend_usd=0`. The frozen `timeout_seconds` is enforced across target preparation and protocol work. Cancellation is durable via `across-edge-worker cancel --state-dir <dir>` and is checked at safe boundaries; controlled child process groups are terminated on cancellation/timeout.

RPC URLs must be exact credential-free HTTPS allowlist entries: redirects, embedded credentials and query strings are rejected. Remote target repositories are credential-free HTTPS only; local frozen checkouts are allowed for controlled qualification. Unsigned transaction analysis rejects signatures, private keys, mnemonics and seed material.

Worker artifacts are secret-scanned before a terminal `WorkerResult` is emitted. Any task that requires external protocol mutation returns `CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY` before target/protocol execution.
