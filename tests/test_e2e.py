from across_edge.instrumentation import CandidateInstrumentation
from across_edge.model import DepositEvent,FillEvent
from across_edge.observer import Observer
from across_edge.reporting import build_report
from across_edge.storage import Store

def test_end_to_end_shadow_fixture(tmp_path):
    s=Store(tmp_path/"e.sqlite");o=Observer(s);i=CandidateInstrumentation(s);d=DepositEvent(1,42161,9,"d","r","i","o",100,99,"",0,1000,10,"dep",100);rec=o.ingest_deposit(d,"run");i.mark(rec,"T0",at_ns=100);i.mark(rec,"T1",at_ns=200,eligible=True);i.mark(rec,"T2",at_ns=300,simulation_result="success");i.mark(rec,"T3",at_ns=400,transaction_ready=True);o.ingest_fill(FillEvent(1,42161,9,"winner",1,12,"fill",102),"run");report=build_report(s,"run");assert report["observed_candidates"]==1;assert report["eligible_candidates"]==1;assert report["competitors"][0]["relayer"]=="winner";assert report["warning"].startswith("READY_BEFORE_WINNER");s.close()
