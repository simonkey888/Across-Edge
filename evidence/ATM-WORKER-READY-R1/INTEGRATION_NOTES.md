# ATM integration notes

```text
WORKER_ID=across-edge
WORKER_REPO=https://github.com/simonkey888/Across-Edge
WORKER_ENTRYPOINT=across-edge-worker run --job <json> --state-dir <dir> --output-dir <dir>
WORKER_PROTOCOL_VERSION=across-edge-worker/v1
CAPABILITIES_PROVEN=event_log_decoding,chain_provenance,sdk_client_repair,unsigned_transaction_validation,relayer_reconciliation,fee_logic_verification
INSTALL/PREPARE_COMMANDS=python -m pip install -e .
NETWORK_POLICY=exact HTTPS allowlist; read-only JSON-RPC; redirects forbidden
CHAIN_POLICY=explicit allowed_chain_ids; chainId + block provenance required
EXPECTED_ARTIFACTS=worker-result.json,analysis.json,patch.diff,progress receipts,chain evidence
MAX_CONCURRENCY_RECOMMENDATION=1
COST_CEILING_USD=0
FINANCIAL_AUTHORITY=0
CLAIM_AUTHORITY=0
SUBMISSION_AUTHORITY=0
MODEL_AUTHORITY=0
EXTERNAL_PROTOCOL_MUTATION_AUTHORITY=0
PROJECT_CORE_CONTINUES=YES
```
