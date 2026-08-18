from __future__ import annotations
import hashlib,json
from dataclasses import asdict,dataclass,field
from datetime import datetime,timezone
from typing import Any
from . import WORKER_ID,WORKER_PROTOCOL_VERSION,WORKER_VERSION
TERMINAL_LEASE_STATES={"COMPLETED","CANCELLED","EXPIRED","REVOKED","TERMINAL"}
PROVEN_CAPABILITIES={"event_log_decoding","chain_provenance","sdk_client_repair","unsigned_transaction_validation","relayer_reconciliation","fee_logic_verification"}
def canonical_json(value:Any)->str:return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha256_json(value:Any)->str:return hashlib.sha256(canonical_json(value).encode()).hexdigest()
def utc_now()->str:return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def parse_time(value:str)->datetime:
 parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
 if parsed.tzinfo is None:raise ValueError("timestamp_must_be_timezone_aware")
 return parsed.astimezone(timezone.utc)
@dataclass(frozen=True)
class WorkerJob:
 schema_version:str;job_id:str;canonical_opportunity_id:str;worker_id:str;work_lease_id:str;scope_hash:str;frozen_acceptance_criteria:dict[str,Any];target_repository:str;target_base_sha:str;allowed_paths:tuple[str,...];required_capabilities:tuple[str,...];structured_requirements:dict[str,Any];expected_deliverable:dict[str,Any];deterministic_checks:tuple[dict[str,Any],...];allowed_chain_ids:tuple[int,...]=();allowed_read_endpoints:tuple[str,...]=();max_spend_usd:int=0;lease_status:str="ACTIVE";lease_expires_at:str="";timeout_seconds:int=300
 @classmethod
 def from_dict(cls,raw:dict[str,Any])->"WorkerJob":
  if not isinstance(raw,dict):raise ValueError("job_must_be_object")
  required={"schema_version","job_id","canonical_opportunity_id","worker_id","work_lease_id","scope_hash","frozen_acceptance_criteria","target_repository","target_base_sha","allowed_paths","required_capabilities","structured_requirements","expected_deliverable","deterministic_checks","max_spend_usd","lease_status","lease_expires_at"}
  missing=sorted(required-set(raw))
  if missing:raise ValueError("missing_job_fields:"+",".join(missing))
  job=cls(schema_version=str(raw["schema_version"]),job_id=str(raw["job_id"]),canonical_opportunity_id=str(raw["canonical_opportunity_id"]),worker_id=str(raw["worker_id"]),work_lease_id=str(raw["work_lease_id"]),scope_hash=str(raw["scope_hash"]),frozen_acceptance_criteria=dict(raw["frozen_acceptance_criteria"]),target_repository=str(raw["target_repository"]),target_base_sha=str(raw["target_base_sha"]),allowed_paths=tuple(str(x) for x in raw["allowed_paths"]),required_capabilities=tuple(str(x) for x in raw["required_capabilities"]),structured_requirements=dict(raw["structured_requirements"]),expected_deliverable=dict(raw["expected_deliverable"]),deterministic_checks=tuple(dict(x) for x in raw["deterministic_checks"]),allowed_chain_ids=tuple(int(x) for x in raw.get("allowed_chain_ids",[])),allowed_read_endpoints=tuple(str(x) for x in raw.get("allowed_read_endpoints",[])),max_spend_usd=int(raw["max_spend_usd"]),lease_status=str(raw["lease_status"]),lease_expires_at=str(raw["lease_expires_at"]),timeout_seconds=int(raw.get("timeout_seconds",300)))
  job.validate();return job
 def scope_material(self)->dict[str,Any]:
  data=asdict(self);data.pop("scope_hash",None);data["allowed_paths"]=list(self.allowed_paths);data["required_capabilities"]=list(self.required_capabilities);data["deterministic_checks"]=list(self.deterministic_checks);data["allowed_chain_ids"]=list(self.allowed_chain_ids);data["allowed_read_endpoints"]=list(self.allowed_read_endpoints);return data
 def computed_scope_hash(self)->str:return sha256_json(self.scope_material())
 def validate(self)->None:
  if self.schema_version!=WORKER_PROTOCOL_VERSION:raise ValueError("unsupported_worker_protocol")
  if self.worker_id!=WORKER_ID:raise ValueError("worker_id_mismatch")
  if not self.job_id or not self.work_lease_id or not self.canonical_opportunity_id:raise ValueError("job_or_lease_identity_missing")
  if len(self.target_base_sha)!=40 or any(c not in "0123456789abcdef" for c in self.target_base_sha.lower()):raise ValueError("invalid_target_base_sha")
  if self.max_spend_usd!=0:raise ValueError("nonzero_spend_forbidden")
  status=self.lease_status.upper()
  if status in TERMINAL_LEASE_STATES:raise ValueError("terminal_lease")
  if status!="ACTIVE":raise ValueError("lease_not_active")
  if not self.lease_expires_at:raise ValueError("lease_expiry_required")
  if parse_time(self.lease_expires_at)<=datetime.now(timezone.utc):raise ValueError("expired_lease")
  if self.timeout_seconds<=0 or self.timeout_seconds>3600:raise ValueError("invalid_timeout")
  if self.scope_hash!=self.computed_scope_hash():raise ValueError("scope_hash_mismatch")
  if not self.allowed_paths:raise ValueError("allowed_paths_required")
  if not self.required_capabilities:raise ValueError("required_capabilities_required")
  if self.structured_requirements.get("external_protocol_mutation") is True:raise PermissionError("CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY:external_protocol_mutation")
  unsupported=sorted(set(self.required_capabilities)-PROVEN_CAPABILITIES)
  if unsupported:raise PermissionError("CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY:unsupported_capability:"+",".join(unsupported))
  requested_chains={int(x) for x in self.structured_requirements.get("requested_chain_ids",[])}
  if not requested_chains.issubset(set(self.allowed_chain_ids)):raise ValueError("disallowed_chain")
  requested_endpoints=set(self.structured_requirements.get("requested_read_endpoints",[]))
  if not requested_endpoints.issubset(set(self.allowed_read_endpoints)):raise ValueError("disallowed_endpoint")
@dataclass
class WorkerResult:
 schema_version:str=WORKER_PROTOCOL_VERSION;worker_id:str=WORKER_ID;worker_version:str=WORKER_VERSION;source_sha:str="";job_id:str="";work_lease_id:str="";scope_hash:str="";status:str="";started_at:str="";finished_at:str="";content_hashes:dict[str,str]=field(default_factory=dict);artifact_hashes:dict[str,str]=field(default_factory=dict);patch_identity:str|None=None;local_commit_identity:str|None=None;tests:list[dict[str,Any]]=field(default_factory=list);chain_evidence_refs:list[dict[str,Any]]=field(default_factory=list);limitations:list[str]=field(default_factory=list);error_class:str|None=None;outgoing_spend_usd:int=0;authoritative_acceptance:bool=False;paid:bool=False;withdrawable:bool=False;realized_profit:bool=False;executed_onchain:bool=False;payout_success:bool=False
 def validate(self)->None:
  if self.schema_version!=WORKER_PROTOCOL_VERSION or self.worker_id!=WORKER_ID:raise ValueError("result_identity_invalid")
  if self.outgoing_spend_usd!=0:raise ValueError("result_spend_nonzero")
  if any({"authoritative_acceptance":self.authoritative_acceptance,"paid":self.paid,"withdrawable":self.withdrawable,"realized_profit":self.realized_profit,"executed_onchain":self.executed_onchain,"payout_success":self.payout_success}.values()):raise ValueError("forbidden_authoritative_or_economic_claim")
  if self.source_sha and (len(self.source_sha)!=40 or any(c not in "0123456789abcdef" for c in self.source_sha.lower())):raise ValueError("result_source_sha_invalid")
  if not self.finished_at or not self.started_at:raise ValueError("result_timestamps_required")
 def to_dict(self)->dict[str,Any]:self.validate();return asdict(self)
 def content_hash(self)->str:return sha256_json(self.to_dict())
