#!/usr/bin/env python3
import json,tempfile,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from across_edge.coordinator import ShadowCoordinator,PREFIX
from across_edge.storage import Store
N=1000
with tempfile.TemporaryDirectory() as d:
 s=Store(Path(d)/'x.db');c=ShadowCoordinator(s,'bench');samples=[]
 for i in range(N):
  e={'version':2,'stage':'T0','trace_id':f't{i}','deposit_key':f'42161:{i}','origin_chain_id':42161,'deposit_id':i,'destination_chain_id':8453,'candidate_type':'open','wall_utc':'2026-08-10T00:00:00Z'};line=PREFIX+json.dumps(e);t=time.perf_counter_ns();c.ingest_line(line);samples.append((time.perf_counter_ns()-t)/1000)
 s.close()
xs=sorted(samples);pct=lambda p:xs[int(round((len(xs)-1)*p))]
print(json.dumps({'component':'python_coordinator_parse_persist_T0','iterations':N,'p50_us':pct(.5),'p90_us':pct(.9),'p99_us':pct(.99),'upstream_typescript_emitter_overhead':'UNKNOWN_UNTIL_PINNED_UPSTREAM_BUILD_AND_RUN'},sort_keys=True))
