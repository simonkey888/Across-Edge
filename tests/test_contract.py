from __future__ import annotations
import tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from across_edge_worker.models import WorkerJob,WorkerResult,sha256_json,utc_now
from helpers import job_dict,make_repo
class ContractTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.repo,self.sha=make_repo(self.root/"target")
 def tearDown(self):self.tmp.cleanup()
 def reb(self,raw):m=dict(raw);m.pop("scope_hash");raw["scope_hash"]=sha256_json(m);return raw
 def test_valid_scope_binding(self):j=WorkerJob.from_dict(job_dict(self.repo,self.sha));self.assertEqual(j.scope_hash,j.computed_scope_hash());self.assertEqual(j.max_spend_usd,0)
 def test_scope_tamper_fails_closed(self):
  r=job_dict(self.repo,self.sha);r["target_base_sha"]="a"*40
  with self.assertRaisesRegex(ValueError,"scope_hash_mismatch"):WorkerJob.from_dict(r)
 def test_wrong_worker_fails_closed(self):
  r=job_dict(self.repo,self.sha);r["worker_id"]="other"
  with self.assertRaisesRegex(ValueError,"worker_id_mismatch"):WorkerJob.from_dict(self.reb(r))
 def test_terminal_expired_and_nonactive_lease_fail_closed(self):
  r=job_dict(self.repo,self.sha);r["lease_status"]="CANCELLED"
  with self.assertRaisesRegex(ValueError,"terminal_lease"):WorkerJob.from_dict(self.reb(r))
  r=job_dict(self.repo,self.sha);r["lease_status"]="PENDING"
  with self.assertRaisesRegex(ValueError,"lease_not_active"):WorkerJob.from_dict(self.reb(r))
  r=job_dict(self.repo,self.sha);r["lease_expires_at"]=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
  with self.assertRaisesRegex(ValueError,"expired_lease"):WorkerJob.from_dict(self.reb(r))
 def test_nonzero_spend_fails_closed(self):
  r=job_dict(self.repo,self.sha);r["max_spend_usd"]=1
  with self.assertRaisesRegex(ValueError,"nonzero_spend_forbidden"):WorkerJob.from_dict(self.reb(r))
 def test_chain_and_endpoint_allowlists_fail_closed(self):
  r=job_dict(self.repo,self.sha);r["structured_requirements"]["requested_chain_ids"]=[1]
  with self.assertRaisesRegex(ValueError,"disallowed_chain"):WorkerJob.from_dict(self.reb(r))
  r=job_dict(self.repo,self.sha);r["structured_requirements"]["requested_read_endpoints"]=["https://evil.invalid"]
  with self.assertRaisesRegex(ValueError,"disallowed_endpoint"):WorkerJob.from_dict(self.reb(r))
 def test_external_mutation_is_authority_refusal(self):
  with self.assertRaisesRegex(PermissionError,"CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY"):WorkerJob.from_dict(job_dict(self.repo,self.sha,mutation=True))
 def test_unsupported_capability_is_authority_refusal(self):
  with self.assertRaisesRegex(PermissionError,"unsupported_capability"):WorkerJob.from_dict(job_dict(self.repo,self.sha,capabilities=["deploy_contract"],actions=[]))
 def test_chain_evidence_cannot_turn_worker_result_into_authoritative_acceptance(self):
  n=utc_now();r=WorkerResult(source_sha="a"*40,job_id="j",work_lease_id="l",scope_hash="h",status="RESULT_READY",started_at=n,finished_at=n,chain_evidence_refs=[{"chain_id":42161,"block_number":1,"block_hash":"0x"+"11"*32,"as_of":n}],authoritative_acceptance=True)
  with self.assertRaisesRegex(ValueError,"forbidden_authoritative_or_economic_claim"):r.validate()
 def test_result_cannot_claim_economic_or_external_acceptance(self):
  n=utc_now();r=WorkerResult(source_sha="a"*40,job_id="j",work_lease_id="l",scope_hash="h",status="RESULT_READY",started_at=n,finished_at=n);r.validate()
  for f in ("paid","withdrawable","realized_profit","executed_onchain","payout_success","authoritative_acceptance"):
   setattr(r,f,True)
   with self.assertRaisesRegex(ValueError,"forbidden_authoritative_or_economic_claim"):r.validate()
   setattr(r,f,False)
if __name__=="__main__":unittest.main()
