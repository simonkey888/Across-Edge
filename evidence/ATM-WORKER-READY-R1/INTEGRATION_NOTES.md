# ATM integration notes

Proposed handoff after independent Project AUD pass:

```text
WORKER_ID=across-edge
WORKER_ENTRYPOINT=across-edge-worker
WORKER_PROTOCOL_VERSION=atm-worker/v1
MAX_CONCURRENCY_RECOMMENDATION=1
COST_CEILING_USD=0
FINANCIAL_AUTHORITY=0
CLAIM_AUTHORITY=0
SUBMISSION_AUTHORITY=0
MODEL_AUTHORITY=0
EXTERNAL_PROTOCOL_MUTATION_AUTHORITY=0
PROJECT_CORE_CONTINUES=YES
```

The worker accepts only frozen jobs with exact target SHA/path/capability/chain/endpoint scope. ATM activation/source-pin remains a separate control-repo order. Worker readiness alone does not enable it.
