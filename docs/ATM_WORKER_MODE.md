# Across-Edge ATM worker mode

Across-Edge has two independent operating modes.

`ACROSS_EDGE_RESEARCH_MODE` is the project-owned relayer/shadow research path governed by its own orders and PR. Nothing in ATM worker readiness grants it financial authority.

`ACROSS_EDGE_ATM_WORKER_MODE` is a read-only Web3/protocol engineering worker. It accepts frozen ATM jobs, copies an exact target SHA into an isolated workspace, performs only allowlisted local analysis/repair operations, verifies deterministic evidence, and returns a structured content-hashed result.

Worker mode has zero outgoing spend and zero signing, broadcast, write-RPC, claim, submission, payment and external protocol mutation authority. A job that requires those actions is refused before the external action.

Machine entrypoint:

```text
across-edge-worker capabilities
across-edge-worker validate JOB.json
across-edge-worker run JOB.json --target-checkout TARGET --run-root RUN_DIR
across-edge-worker cancel --run-root RUN_DIR
```

Target-provided commands are intentionally not executed in R1. Adding arbitrary target execution requires a separately proven OS-level sandbox and does not follow automatically from this worker contract.
