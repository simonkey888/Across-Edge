import pytest
from across_edge.instrumentation import CandidateInstrumentation
from across_edge.model import ShadowRecord
from across_edge.storage import Store

def rec():return ShadowRecord(1,"r","1:1",1,1,42161,"i","o",1,1,"",0,"open")
def test_stage_marks_are_monotonic_and_persisted(tmp_path):
    s=Store(tmp_path/"i.sqlite");i=CandidateInstrumentation(s);r=rec();i.mark(r,"T0",at_ns=10);i.mark(r,"T1",at_ns=20,eligible=True,profitability_decision="profitable");i.mark(r,"T2",at_ns=30,simulation_result="success");i.mark(r,"T3",at_ns=40,transaction_ready=True);row=s.shadow_rows("r")[0];assert(row["t0_monotonic_ns"],row["t3_monotonic_ns"])==(10,40);assert row["transaction_ready"] is True;s.close()
def test_backwards_stage_rejected(tmp_path):
    s=Store(tmp_path/"i.sqlite");i=CandidateInstrumentation(s);r=rec();i.mark(r,"T0",at_ns=20)
    with pytest.raises(RuntimeError):i.mark(r,"T1",at_ns=19)
    s.close()
