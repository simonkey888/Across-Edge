from __future__ import annotations
import tempfile,unittest
from pathlib import Path
from across_edge_worker.capabilities import CapabilityContext,apply_text_repair,decode_transfer_log,reconcile_attempts,validate_unsigned_transaction,verify_fee_logic
from across_edge_worker.lifecycle import LifecycleStore
from helpers import make_repo
class CapabilityTests(unittest.TestCase):
 def test_event_log_decoding(self):
  log={"topics":["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef","0x"+"0"*24+"11"*20,"0x"+"0"*24+"22"*20],"data":"0x"+f"{9:064x}","blockNumber":"0x20","blockHash":"0x"+"33"*32};self.assertEqual(decode_transfer_log(log)["value"],9)
 def test_unsigned_transaction_data_only(self):
  r=validate_unsigned_transaction({"chain_id":8453,"to":"0x"+"11"*20,"data":"0x1234","value":0},(8453,));self.assertFalse(r["executed"])
  with self.assertRaisesRegex(ValueError,"signed_transaction_material_forbidden"):validate_unsigned_transaction({"chain_id":8453,"to":"0x"+"11"*20,"data":"0x","value":0,"signature":"x"},(8453,))
 def test_relayer_reconciliation_dedup_and_ambiguity(self):
  r=reconcile_attempts([{"deposit_id":"d","evaluation_id":"e","decision":"profitable"},{"deposit_id":"d","evaluation_id":"e","decision":"unprofitable"}]);self.assertEqual(r["deduped_count"],1);self.assertEqual(r["ambiguous_count"],1)
 def test_fee_logic_is_derived_not_realized(self):
  r=verify_fee_logic({"gross_fee_wei":100,"gas_cost_wei":10,"capital_cost_wei":20,"rebalance_cost_wei":5});self.assertEqual(r["net_fee_wei"],65);self.assertFalse(r["realized_profit"])
 def test_repair_is_idempotent_under_recovery(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);repo,_=make_repo(root/"repo");store=LifecycleStore(root/"s.db");eid=store.begin(job_id="j",lease_id="l",scope_hash="s",source_sha="a"*40);ctx=CapabilityContext(repo,("client.py",),store,eid,(),());a={"path":"client.py","old":"    return events\n","new":"    return events[-128:]\n","repair_id":"r"};x=apply_text_repair(ctx,a);y=apply_text_repair(ctx,a);self.assertEqual(x["patch"],y["patch"]);store.close()
if __name__=="__main__":unittest.main()
