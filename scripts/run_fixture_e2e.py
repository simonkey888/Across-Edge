#!/usr/bin/env python3
from pathlib import Path
from across_edge.instrumentation import CandidateInstrumentation
from across_edge.model import DepositEvent,FillEvent
from across_edge.observer import Observer
from across_edge.reporting import export_artifacts
from across_edge.storage import Store
ROOT=Path(__file__).resolve().parents[1];out=ROOT/"evidence"/"fixture-e2e";out.mkdir(parents=True,exist_ok=True);db=out/"fixture.sqlite";db.unlink(missing_ok=True)
s=Store(db);o=Observer(s);inst=CandidateInstrumentation(s);run="fixture-e2e"
d=DepositEvent(1,42161,4242,"0x"+"11"*32,"0x"+"22"*32,"0x"+"33"*32,"0x"+"44"*32,1_000_000,995_000,"0x"+"00"*32,0,200,100,"0xdeposit",100);r=o.ingest_deposit(d,run)
inst.mark(r,"T0",at_ns=1_000_000_000,t0_wall_utc="2026-08-10T02:40:00Z");inst.mark(r,"T1",at_ns=1_030_000_000,eligible=True,profitability_decision="profitable");inst.mark(r,"T2",at_ns=1_060_000_000,simulation_result="success");inst.mark(r,"T3",at_ns=1_080_000_000,transaction_ready=True)
o.ingest_fill(FillEvent(1,42161,4242,"0x"+"55"*32,1,101,"0xfill",101),run,observed_monotonic_ns=1_250_000_000,observed_wall_utc="2026-08-10T02:40:01Z");print(export_artifacts(s,run,out));s.close();db.unlink(missing_ok=True)
