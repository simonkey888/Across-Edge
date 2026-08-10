from across_edge.model import DepositEvent,ShadowRecord
from across_edge.reporting import build_report,export_artifacts
from across_edge.storage import Store

def test_storage_and_report_unknowns_are_not_zero(tmp_path):
    s=Store(tmp_path/"x.sqlite");d=DepositEvent(1,42161,1,"d","r","i","o",10,9,"",0,1000,1,"tx",100);s.upsert_deposit(d);s.upsert_shadow(ShadowRecord(1,"run","1:1",1,1,42161,"i","o",10,9,"",0,"open",t0_monotonic_ns=100,t1_monotonic_ns=200));rep=build_report(s,"run");assert rep["median_t0_t1_ms"]==0.0001;assert rep["median_t1_t2_ms"] is None;assert rep["eligible_under_25"] is None;out=tmp_path/"out";export_artifacts(s,"run",out);assert(out/"run-metadata.json").exists() and (out/"competitors.csv").exists();s.close()
