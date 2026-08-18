# PROJECT_PRESERVATION

`ACROSS_EDGE_RESEARCH_MODE` and `ACROSS_EDGE_ATM_WORKER_MODE` are separate modes.

- Worker branch is dedicated and stacked on the frozen relayer branch; no commit is added to PR #2 by worker implementation.
- Worker entrypoint is `across-edge-worker`; relayer entrypoint remains `across-edge` plus existing shadow scripts/workflows.
- Worker does not require the relayer process to be running.
- Existing relayer code does not import or require the ATM worker module.
- Worker external protocol mutation authority is zero and it cannot mutate relayer deployment/governance state.
- Worker fee/profitability verification takes pinned inputs and cannot claim realized relayer profit.
- ORDER-011 remains governed by its own Issue #10, branch workflow and evidence.
- `main` remains unchanged for this readiness PR.
