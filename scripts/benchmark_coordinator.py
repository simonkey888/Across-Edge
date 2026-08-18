#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,platform,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from across_edge.coordinator import PREFIX,ShadowCoordinator
from across_edge.model import ShadowRecord
from across_edge.storage import Store
def pct(xs,p):return sorted(xs)[int(round((len(xs)-1)*p))]/1000
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--records',type=int,default=5000);ap.add_argument('--samples',type=int,default=1000);ap.add_argument('--out');a=ap.parse_args()
 with tempfile.TemporaryDirectory() as td:
  s=Store(Path(td)/'b.db')
  for i in range(a.records):s.upsert_shadow(ShadowRecord(3,'bench',f'1:{i}',1,i,8453,'i','o',1,1,'',0,'other',trace_id=f't{i}',t0_monotonic_ns=1),commit=False)
  s.db.commit();c=ShadowCoordinator(s,'bench');lat=[]
  for n in range(a.samples):
   i=n%a.records;e={'version':3,'stage':'T0','trace_id':f't{i}','deposit_key':f'1:{i}','origin_chain_id':1,'deposit_id':i,'destination_chain_id':8453,'deposit_block':1,'max_block_number':1,'live_equivalent_confirmations_satisfied':True,'source_monotonic_ns':'0'};line=PREFIX+json.dumps(e,separators=(',',':'));t=time.perf_counter_ns();c.ingest_line(line);lat.append(time.perf_counter_ns()-t)
  payload={'records':a.records,'samples':a.samples,'p50_us':pct(lat,.5),'p90_us':pct(lat,.9),'p99_us':pct(lat,.99),'python':sys.version.split()[0],'platform':platform.platform(),'measurement':'local receive->parse->indexed lookup->sqlite upsert; Node source clock excluded'};s.close()
 text=json.dumps(payload,indent=2,sort_keys=True)+'\n';print(text,end='')
 if a.out:Path(a.out).write_text(text)
if __name__=='__main__':main()
