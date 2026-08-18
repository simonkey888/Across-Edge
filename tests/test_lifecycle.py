import tempfile,unittest
from pathlib import Path
from across_edge_worker.lifecycle import LifecycleStore
class LifecycleTests(unittest.TestCase):
 def test_ack_progress_and_read_replay_are_durable_and_idempotent(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"s.db";s=LifecycleStore(p);eid=s.begin(job_id="j",lease_id="l",scope_hash="s",source_sha="a"*40);s.advance(eid,"ACK");self.assertEqual(s.receipt(eid,"ack","ACK",{"lease":"l"}),s.receipt(eid,"ack","ACK",{"lease":"l"}));s.record_read(eid,"r",{"m":1},{"x":1});self.assertEqual(s.cached_read(eid,"r",{"m":1}),{"x":1});s.close();s=LifecycleStore(p);self.assertEqual(s.phase(eid),"ACK");s.close()
if __name__=="__main__":unittest.main()
