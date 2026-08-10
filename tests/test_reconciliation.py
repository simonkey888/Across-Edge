from across_edge.model import ShadowRecord
from across_edge.observer import Observer
from across_edge.storage import Store
from conftest import make_deposit,make_fill
def shadow(store,key='42161:7',trace='t'):
 r=ShadowRecord(4,'r',key,42161,7,8453,'i','o',1,1,'',0,'open',trace_id=trace,ta_monotonic_ns=100,t0_monotonic_ns=90,t1_monotonic_ns=110,t2_monotonic_ns=120,t3_monotonic_ns=130,live_equivalent_confirmations_satisfied=True,transaction_ready=True);store.upsert_shadow(r);return r
def test_shadow_before_fill(tmp_path):
 s=Store(tmp_path/'x');o=Observer(s);o.ingest_deposit(make_deposit(),'r',destination_time=100,trace_id='t');r=s.shadow_by_trace('r','t');r['ta_monotonic_ns']=100;r['t3_monotonic_ns']=130;r['live_equivalent_confirmations_satisfied']=True;s.upsert_shadow(ShadowRecord(**r));o.ingest_fill(make_fill(),'r',observed_monotonic_ns=200);assert s.shadow_by_trace('r','t')['winner_tx_hash']=='0xf1';s.close()
def test_fill_before_shadow_and_restart(tmp_path):
 p=tmp_path/'x';s=Store(p);o=Observer(s);o.ingest_fill(make_fill(),'r',observed_monotonic_ns=200);s.close();s=Store(p);o=Observer(s);o.ingest_deposit(make_deposit(),'r',destination_time=100,trace_id='t');assert s.shadow_by_trace('r','t')['winner_tx_hash']=='0xf1';s.close()
def test_two_fills_choose_chain_order_not_arrival(tmp_path):
 s=Store(tmp_path/'x');o=Observer(s);o.ingest_deposit(make_deposit(),'r',destination_time=100,trace_id='t');o.ingest_fill(make_fill(tx='0xf2',block=13,idx=1),'r',observed_monotonic_ns=300);o.ingest_fill(make_fill(tx='0xf1',block=12,idx=9),'r',observed_monotonic_ns=250);assert s.shadow_by_trace('r','t')['winner_tx_hash']=='0xf1';s.close()
def test_duplicate_overlap_is_idempotent(tmp_path):
 s=Store(tmp_path/'x');o=Observer(s);o.ingest_deposit(make_deposit(),'r',destination_time=100,trace_id='t');f=make_fill();assert o.ingest_fill(f,'r',observed_monotonic_ns=200);first=s.shadow_by_trace('r','t')['tw_monotonic_ns'];assert not o.ingest_fill(f,'r',observed_monotonic_ns=999);assert s.shadow_by_trace('r','t')['tw_monotonic_ns']==first;s.close()
def test_reorg_first_fill_reveals_later_canonical_fill(tmp_path):
 s=Store(tmp_path/'x');o=Observer(s);o.ingest_deposit(make_deposit(),'r',destination_time=100,trace_id='t');o.ingest_fill(make_fill(tx='0xf1',block=12,idx=1),'r',observed_monotonic_ns=200);o.ingest_fill(make_fill(tx='0xf2',block=13,idx=1),'r',observed_monotonic_ns=300);assert s.shadow_by_trace('r','t')['winner_tx_hash']=='0xf1';s.rewind_chain(8453,12);o=Observer(s);o.ingest_fill(make_fill(tx='0xf2',block=13,idx=1),'r',observed_monotonic_ns=400);assert s.shadow_by_trace('r','t')['winner_tx_hash']=='0xf2';s.close()
