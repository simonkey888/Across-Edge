from across_edge.observer import Observer
from across_edge.storage import Store
from conftest import make_deposit,make_fill
def snapshot(s):return {'deposits':s.all_deposits(),'fills':s.all_fills(),'shadow':s.shadow_rows('r'),'transitions':s.transitions('r','t')}
def build(path,with_orphan=False):
 s=Store(path);o=Observer(s);o.ingest_deposit(make_deposit(exclusive='0x'+'a'*64,deadline=200),'r',destination_time=100,trace_id='t',source_block_number=5,source_block_hash='0xd5')
 if with_orphan:o.refresh_candidate_states('r',8453,201,source_block_number=12,source_block_hash='0xorphan');o.ingest_fill(make_fill(tx='0xorphan',block=12,idx=1),'r',observed_monotonic_ns=200)
 return s,o
def test_reorg_rewind_replay_equals_clean_canonical_ingest(tmp_path):
 dirty,o=build(tmp_path/'dirty',True);dirty.rewind_chain(8453,12);o=Observer(dirty);o.refresh_candidate_states('r',8453,150,source_block_number=12,source_block_hash='0xcanon');o.ingest_fill(make_fill(tx='0xcanon',block=12,idx=1),'r',observed_monotonic_ns=250,observed_wall_utc='2026-08-10T00:00:00Z');clean,o2=build(tmp_path/'clean',False);o2.refresh_candidate_states('r',8453,150,source_block_number=12,source_block_hash='0xcanon');o2.ingest_fill(make_fill(tx='0xcanon',block=12,idx=1),'r',observed_monotonic_ns=250,observed_wall_utc='2026-08-10T00:00:00Z');a,b=snapshot(dirty),snapshot(clean)
 for x in (a,b):
  for t in x['transitions']:t.pop('observed_wall_utc',None)
  for r in x['shadow']:
   for t in r['candidate_state_history']:t.pop('observed_wall_utc',None)
 assert a==b;dirty.close();clean.close()
