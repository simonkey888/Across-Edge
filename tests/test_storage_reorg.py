from across_edge.model import DepositEvent,FillEvent,ShadowRecord
from across_edge.storage import Store
def test_rewind_removes_orphan_events_and_winner(tmp_path):
 s=Store(tmp_path/'x.db');d=DepositEvent(42161,8453,1,'d','r','i','o',1,1,'',0,9,100,'0xd',1,block_hash='0xb',log_index=1);s.upsert_deposit(d);f=FillEvent(1,8453,2,'r',1,120,'0xf',2,block_hash='0xc',log_index=2);s.insert_fill(f);r=ShadowRecord(2,'run','1:2',1,2,8453,'i','o',1,1,'',0,'open',trace_id='t',winner_tx_hash='0xf',winner_block=120);s.upsert_shadow(r);s.rewind_chain(8453,110);assert s.all_fills()==[];assert s.shadow_rows('run')[0]['winner_tx_hash']=='';s.rewind_chain(42161,90);assert s.all_deposits()==[];s.close()
def test_rewind_one_destination_does_not_delete_legacy_fill_on_another_chain(tmp_path):
 s=Store(tmp_path/'x.db');a=FillEvent(1,8453,1,'r',1,120,'0xfa',2,log_index=1);b=FillEvent(1,42161,2,'r',1,121,'0xfb',2,log_index=1);s.insert_fill(a);s.insert_fill(b);s.rewind_chain(8453,110);rows=s.all_fills();assert len(rows)==1 and rows[0]['tx_hash']=='0xfb';s.close()
