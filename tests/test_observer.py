from across_edge.model import DepositEvent,FillEvent
from across_edge.observer import Observer,competitor_scoreboard
from across_edge.storage import Store

def dep(exclusive="0x"+"0"*64,deadline=0):return DepositEvent(1,42161,7,"0x"+"1"*64,"0x"+"2"*64,"0x"+"3"*64,"0x"+"4"*64,1000,990,exclusive,deadline,999999,10,"0xdep",100)
def test_ingest_dedup_and_correlate(tmp_path):
    s=Store(tmp_path/"x.sqlite");o=Observer(s);r=o.ingest_deposit(dep(),"r1");assert r.candidate_type=="open";f=FillEvent(1,42161,7,"0x"+"5"*64,1,12,"0xfill",102);assert o.ingest_fill(f,"r1") is True;assert o.ingest_fill(f,"r1") is False;row=s.shadow_rows("r1")[0];assert row["winner_tx_hash"]=="0xfill";assert row["winner_latency_ms"]==2000.0;s.close()
def test_exclusive_and_stepin(tmp_path):
    s=Store(tmp_path/"x.sqlite");o=Observer(s);assert o.ingest_deposit(dep("0x"+"a"*64,200),"r").candidate_type=="exclusive_other";s.close()
def test_scoreboard():
    board=competitor_scoreboard([dep().__dict__],[FillEvent(1,42161,7,"0xabc",1,12,"0xf",102).__dict__]);assert board[0]["fills_observed"]==1 and board[0]["median_deposit_to_fill_ms"]==2000.0
