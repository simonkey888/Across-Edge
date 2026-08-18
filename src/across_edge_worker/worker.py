from __future__ import annotations
import json,os,subprocess,time
from pathlib import Path
from .capabilities import CapabilityContext,apply_text_repair,chain_provenance,decode_transfer_log,reconcile_attempts,static_check,validate_unsigned_transaction,verify_fee_logic
from .lifecycle import LifecycleStore
from .models import WorkerJob,WorkerResult,sha256_json,utc_now
from .security import prepare_isolated_target,scan_text_for_secrets,scan_tree_for_secrets,sha256_file,snapshot_tree_hash
def _source_sha():
 override=os.environ.get("ACROSS_EDGE_WORKER_SOURCE_SHA","").strip().lower()
 if len(override)==40 and all(c in "0123456789abcdef" for c in override):return override
 root=Path(__file__).resolve().parents[2]
 try:return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
 except Exception:return "0"*40
def _maybe_crash(point):
 if os.environ.get("ACROSS_EDGE_WORKER_CRASH_AT")==point:os._exit(91)
def _write_json(path,payload):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n");return sha256_file(path)
def _guard(cancel_marker:Path,deadline:float)->None:
 if cancel_marker.exists():raise InterruptedError("worker_cancelled")
 if time.monotonic()>=deadline:raise TimeoutError("worker_timeout")
def _remaining(deadline:float,ceiling:float=120)->float:
 remaining=deadline-time.monotonic()
 if remaining<=0:raise TimeoutError("worker_timeout")
 return min(ceiling,remaining)
def _cannot_handle(raw,output_dir,reason):
 now=utc_now();result=WorkerResult(source_sha=_source_sha(),job_id=str(raw.get("job_id") or "UNKNOWN"),work_lease_id=str(raw.get("work_lease_id") or "UNKNOWN"),scope_hash=str(raw.get("scope_hash") or "UNKNOWN"),status="CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY",started_at=now,finished_at=now,limitations=[reason],error_class="AUTHORITY_BOUNDARY",outgoing_spend_usd=0);payload=result.to_dict();encoded=json.dumps(payload,sort_keys=True)
 if scan_text_for_secrets(encoded):raise ValueError("worker_result_secret_scan_failed")
 _write_json(output_dir/"worker-result.json",payload);return payload
def run_job(job_path:Path,state_dir:Path,output_dir:Path):
 raw=json.loads(job_path.read_text());output_dir.mkdir(parents=True,exist_ok=True)
 try:job=WorkerJob.from_dict(raw)
 except PermissionError as exc:return _cannot_handle(raw,output_dir,str(exc))
 deadline=time.monotonic()+job.timeout_seconds;state_dir.mkdir(parents=True,exist_ok=True);cancel_marker=state_dir/"cancel.requested";_guard(cancel_marker,deadline);source_sha=_source_sha();store=LifecycleStore(state_dir/"worker.sqlite")
 try:
  eid=store.begin(job_id=job.job_id,lease_id=job.work_lease_id,scope_hash=job.scope_hash,source_sha=source_sha);existing={x["receipt_key"]:x for x in store.list_receipts(eid)};start=existing["receive"]["payload"] if "receive" in existing else store.receipt(eid,"receive","RECEIVE",{"received_at":utc_now(),"scope_hash":job.scope_hash});started_at=str(start["received_at"]);store.advance(eid,"VALIDATE");store.receipt(eid,"validated","VALIDATE",{"worker_id":job.worker_id,"work_lease_id":job.work_lease_id,"scope_hash":job.scope_hash,"target_base_sha":job.target_base_sha,"max_spend_usd":job.max_spend_usd});store.advance(eid,"ACK");existing={x["receipt_key"]:x for x in store.list_receipts(eid)}
  if "ack" not in existing:store.receipt(eid,"ack","ACK",{"job_id":job.job_id,"work_lease_id":job.work_lease_id,"scope_hash":job.scope_hash,"source_sha":source_sha,"ack_at":utc_now()})
  _guard(cancel_marker,deadline);_maybe_crash("after_ack");project_root=Path(__file__).resolve().parents[2];before=snapshot_tree_hash(project_root);workdir=state_dir/"executions"/eid;store.advance(eid,"PREPARE_ISOLATED_TARGET");target=prepare_isolated_target(job.target_repository,job.target_base_sha,workdir,timeout=_remaining(deadline),cancel_marker=cancel_marker);_guard(cancel_marker,deadline);store.receipt(eid,"target-prepared","PROGRESS",{"objective":"isolated_target_exact_sha","target":str(target),"target_base_sha":job.target_base_sha,"project_hash_before":before});ctx=CapabilityContext(target,job.allowed_paths,store,eid,job.allowed_read_endpoints,job.allowed_chain_ids,deadline,cancel_marker);store.advance(eid,"WORK");outputs=[];patches=[];chain_refs=[]
  for index,action in enumerate(list(job.structured_requirements.get("actions",[]))):
   ctx.guard();cap=str(action.get("capability") or "")
   if cap not in job.required_capabilities:raise ValueError("action_capability_not_declared")
   if cap=="event_log_decoding":value=decode_transfer_log(dict(action["log"]))
   elif cap=="chain_provenance":value=chain_provenance(ctx,action);chain_refs.append(value);_maybe_crash("during_rpc")
   elif cap=="sdk_client_repair":value=apply_text_repair(ctx,action);patches.append(str(value["patch"])) if value.get("patch") else None
   elif cap=="unsigned_transaction_validation":value=validate_unsigned_transaction(dict(action["transaction"]),job.allowed_chain_ids)
   elif cap=="relayer_reconciliation":value=reconcile_attempts(list(action["attempts"]))
   elif cap=="fee_logic_verification":value=verify_fee_logic(dict(action["inputs"]))
   else:raise PermissionError("CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY:unsupported_runtime_capability")
   ctx.guard();outputs.append({"capability":cap,"observed":value});store.receipt(eid,f"progress-{index+1}","PROGRESS",{"objective":cap,"index":index+1,"output_hash":sha256_json(value)})
  checks=[static_check(ctx,c) for c in job.deterministic_checks];ctx.guard();store.receipt(eid,"checks-completed","PROGRESS",{"objective":"deterministic_checks","count":len(checks),"checks_hash":sha256_json(checks)});findings=scan_tree_for_secrets(target)
  if findings:raise ValueError("target_artifact_secret_scan_failed:"+",".join(findings))
  after=snapshot_tree_hash(project_root)
  if after!=before:raise ValueError("canonical_across_edge_checkout_mutated")
  report={"schema_version":"across-edge-worker-analysis/v1","job_id":job.job_id,"work_lease_id":job.work_lease_id,"scope_hash":job.scope_hash,"source_sha":source_sha,"target_repository":job.target_repository,"target_base_sha":job.target_base_sha,"outputs":outputs,"checks":checks,"progress_receipts":store.list_receipts(eid),"chain_evidence":chain_refs,"project_hash_before":before,"project_hash_after":after,"external_mutation":False,"outgoing_spend_usd":0,"authoritative_external_acceptance":False};report_path=output_dir/"analysis.json";report_hash=_write_json(report_path,report);store.record_artifact(eid,"analysis.json",report_path,report_hash);patch_path=output_dir/"patch.diff";patch_path.write_text("\n".join(patches));patch_hash=sha256_file(patch_path);store.record_artifact(eid,"patch.diff",patch_path,patch_hash);_maybe_crash("after_artifact");ctx.guard();store.advance(eid,"RESULT_READY")
  if scan_tree_for_secrets(output_dir):raise ValueError("published_worker_artifact_secret_scan_failed")
  result=WorkerResult(source_sha=source_sha,job_id=job.job_id,work_lease_id=job.work_lease_id,scope_hash=job.scope_hash,status="RESULT_READY",started_at=started_at,finished_at=utc_now(),content_hashes={"analysis":report_hash},artifact_hashes={"analysis.json":report_hash,"patch.diff":patch_hash},patch_identity=patch_hash if patches else None,tests=checks,chain_evidence_refs=chain_refs,limitations=["Read-only worker result; ATM independently evaluates acceptance.","Fee outputs are derived from pinned inputs and are not realized profit."],outgoing_spend_usd=0);payload=result.to_dict();encoded=json.dumps(payload,sort_keys=True)
  if scan_text_for_secrets(encoded):raise ValueError("worker_result_secret_scan_failed")
  result_hash=_write_json(output_dir/"worker-result.json",payload);store.record_artifact(eid,"worker-result.json",output_dir/"worker-result.json",result_hash);store.terminal(eid,"RESULT_READY");return payload
 finally:store.close()
