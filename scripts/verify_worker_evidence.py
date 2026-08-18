from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence/ATM-WORKER-READY-R1';M=E/'MANIFEST.sha256'
required={'REMOTE_TRUTH.md','WORKER_CONTRACT.json','CAPABILITY_MATRIX.json','SECURITY_BOUNDARY.md','CHAIN_RPC_BOUNDARY.md','NEGATIVE_TESTS.json','CRASH_RECOVERY.json','REAL_WORLD_SHADOW.json','PROJECT_PRESERVATION.md','TEST_RESULTS.txt','CI_EXACT_HEAD.md','INTEGRATION_NOTES.md','CI_RUNTIME_IDENTITY.json'}
if not M.is_file():raise SystemExit('manifest_missing')
expected={}
for line in M.read_text().splitlines():
 if line.strip():digest,relative=line.split('  ',1);expected[relative]=digest
actual={p.name for p in E.iterdir() if p.is_file() and p.name!='MANIFEST.sha256'}
if set(expected)!=actual:raise SystemExit('manifest_file_set_mismatch')
if not required.issubset(actual):raise SystemExit('required_evidence_missing:'+','.join(sorted(required-actual)))
for relative,digest in expected.items():
 path=E/relative
 if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise SystemExit(f'evidence_hash_mismatch:{relative}')
contract=json.loads((E/'WORKER_CONTRACT.json').read_text())
for key,value in {'worker_id':'across-edge','max_spend_usd':0,'external_protocol_mutation_authority':0,'lease_status_required':'ACTIVE'}.items():
 if contract.get(key)!=value:raise SystemExit('worker_contract_invalid:'+key)
for key in ('timeout_policy','cancellation_policy','target_repository_policy','rpc_endpoint_policy'):
 if not contract.get(key):raise SystemExit('worker_contract_missing:'+key)
matrix=json.loads((E/'CAPABILITY_MATRIX.json').read_text())
if not matrix or any(r.get('observed_result')!='PASS' for r in matrix):raise SystemExit('capability_matrix_not_proven')
negative=json.loads((E/'NEGATIVE_TESTS.json').read_text());shadow=json.loads((E/'REAL_WORLD_SHADOW.json').read_text());recovery=json.loads((E/'CRASH_RECOVERY.json').read_text());identity=json.loads((E/'CI_RUNTIME_IDENTITY.json').read_text())
for key in ('non_active_lease_refusal','worker_timeout_enforcement','durable_cancellation','unsigned_private_key_mnemonic_seed_rejection','rpc_credential_query_rejection','target_repository_credential_scheme_rejection','secret_artifact_blocks_terminal_result'):
 if negative.get(key)!='PASS':raise SystemExit('negative_gate_missing:'+key)
if negative.get('status')!='PASS' or negative.get('external_mutation_refusal')!='PASS':raise SystemExit('negative_tests_invalid')
if shadow.get('status')!='PASS' or shadow['can_handle']['status']!='RESULT_READY' or shadow['cannot_handle']['status']!='CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY':raise SystemExit('real_world_shadow_invalid')
if recovery.get('status')!='PASS' or recovery.get('durable_cancellation')!='PASS' or recovery.get('worker_timeout')!='PASS' or any(c.get('status')!='PASS' for c in recovery.get('cases',[])):raise SystemExit('recovery_invalid')
if identity.get('outgoing_spend_usd')!=0 or identity.get('signing')!=0 or identity.get('transaction_broadcast')!=0 or identity.get('write_rpc')!=0:raise SystemExit('runtime_authority_invalid')
print(f'EVIDENCE_MANIFEST=PASS files={len(expected)} source_sha={identity.get("source_sha")}')
