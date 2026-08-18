from across_edge.observer import Observer
from across_edge.storage import Store
from conftest import make_deposit,make_fill
def test_rewind_removes_orphan_events_and_winner(tmp_path):
 s=Store(tmp_path/'x');o=Observer(s);o.ingest_deposit(make_deposit(),'r',destination_time=100,trace_id='t');o.ingest_fill(make_fill(block=120),'r',observed_monotonic_ns=200);assert s.shadow_by_trace('r','t')['winner_tx_hash'];s.rewind_chain(8453,110);assert s.all_fills()==[] and s.shadow_by_trace('r','t')['winner_tx_hash']=='';s.close()
def test_rewind_one_destination_does_not_delete_fill_on_another_chain(tmp_path):
 s=Store(tmp_path/'x');s.insert_fill(make_fill(dest=8453,tx='0xfa',block=120));s.insert_fill(make_fill(dest=42161,deposit_id=8,tx='0xfb',block=121));s.rewind_chain(8453,110);rows=s.all_fills();assert len(rows)==1 and rows[0]['tx_hash']=='0xfb';s.close()
