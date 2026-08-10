from across_edge.model import DepositEvent,FillEvent
from across_edge.observer import Observer
from across_edge.storage import Store
def dep():return DepositEvent(42161,8453,7,'0x'+'1'*64,'0x'+'2'*64,'0x'+'3'*64,'0x'+'4'*64,1000,990,'0x'+'a'*64,200,999,10,'0xdep',100,log_index=1)
def fill(tx='0xf1',idx=2,rel='0x'+'5'*64,block=12):return FillEvent(42161,8453,7,rel,42161,block,tx,102,0,log_index=idx)
def test_duplicate_does_not_mutate_first_winner(tmp_path):
 s=Store(tmp_path/'x.db');o=Observer(s);o.ingest_deposit(dep(),'r',destination_time=100,trace_id='t');row=s.shadow_rows('r')[0];row['t3_monotonic_ns']=100;from across_edge.model import ShadowRecord;s.upsert_shadow(ShadowRecord(**row))
 assert o.ingest_fill(fill(),'r',observed_monotonic_ns=200) is True;first=s.shadow_rows('r')[0].copy();assert o.ingest_fill(fill(),'r',observed_monotonic_ns=999) is False;assert s.shadow_rows('r')[0]['tw_monotonic_ns']==first['tw_monotonic_ns']==200
 assert o.ingest_fill(fill('0xf2',3,'0x'+'6'*64,13),'r',observed_monotonic_ns=1000) is True;assert s.shadow_rows('r')[0]['winner_tx_hash']=='0xf1';assert len(s.all_fills())==2;s.close()
def test_exclusive_transitions_to_step_in_and_survives_restart(tmp_path):
 path=tmp_path/'x.db';s=Store(path);o=Observer(s);r=o.ingest_deposit(dep(),'r',destination_time=200,trace_id='t');assert r.candidate_type=='exclusive_other';o.refresh_candidate_states('r',8453,201);assert s.shadow_rows('r')[0]['candidate_type']=='step_in';s.close();s=Store(path);assert [x['state'] for x in s.transitions('r','t')]==['exclusive_other','step_in'];s.close()
def test_origin_timestamp_is_not_used_as_destination_decision_time(tmp_path):
 s=Store(tmp_path/'x.db');o=Observer(s);r=o.ingest_deposit(dep(),'r',trace_id='t');assert r.candidate_type=='other' and r.decision_destination_time is None;o.refresh_candidate_states('r',8453,200);row=s.shadow_rows('r')[0];assert row['candidate_type']=='exclusive_other' and row['decision_destination_time']==200;s.close()
