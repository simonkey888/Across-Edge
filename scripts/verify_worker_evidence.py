from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];E=ROOT/"evidence/ATM-WORKER-READY-R1";M=E/"MANIFEST.sha256"
if not M.is_file():raise SystemExit("manifest_missing")
expected={}
for line in M.read_text().splitlines():
 if line.strip():digest,relative=line.split("  ",1);expected[relative]=digest
for relative,digest in expected.items():
 path=E/relative
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise SystemExit(f"evidence_hash_mismatch:{relative}")
contract=json.loads((E/"WORKER_CONTRACT.json").read_text())
if contract["worker_id"]!="across-edge" or contract["max_spend_usd"]!=0 or contract["external_protocol_mutation_authority"]!=0:raise SystemExit("worker_contract_authority_invalid")
matrix=json.loads((E/"CAPABILITY_MATRIX.json").read_text())
if not matrix or any(r.get("observed_result")!="PASS" for r in matrix):raise SystemExit("capability_matrix_not_proven")
negative=json.loads((E/"NEGATIVE_TESTS.json").read_text());shadow=json.loads((E/"REAL_WORLD_SHADOW.json").read_text());recovery=json.loads((E/"CRASH_RECOVERY.json").read_text())
if negative.get("status")!="PASS" or negative.get("external_mutation_refusal")!="PASS":raise SystemExit("negative_tests_invalid")
if shadow.get("status")!="PASS" or shadow["can_handle"]["status"]!="RESULT_READY" or shadow["cannot_handle"]["status"]!="CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY":raise SystemExit("real_world_shadow_invalid")
if recovery.get("status")!="PASS" or any(c.get("status")!="PASS" for c in recovery.get("cases",[])):raise SystemExit("crash_recovery_invalid")
print(f"EVIDENCE_MANIFEST=PASS files={len(expected)}")
