# Across-Edge

Low-latency Across relayer research, shadow racing, profitability and execution infrastructure.

Across-Edge keeps two independent modes:

- **`ACROSS_EDGE_RESEARCH_MODE`** — the standalone relayer/shadow-research path. It does not depend on ATM.
- **`ACROSS_EDGE_ATM_WORKER_MODE`** — an additive read-only Web3/protocol engineering worker with zero financial, claim, submission, signing, broadcast, write-RPC, funded-wallet or external-protocol-mutation authority.

Worker details and the machine entrypoint are documented in [`docs/ATM_WORKER_MODE.md`](docs/ATM_WORKER_MODE.md). Worker readiness does not merge, deploy, enable live relaying, or alter the independent shadow-relayer PR.
