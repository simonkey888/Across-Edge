#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from across_edge.rpc import JsonRpcClient
from across_edge.safety import sanitize_text

def pct(xs,p):
 if not xs:return None
 xs=sorted(xs);return xs[int(round((len(xs)-1)*p))]
def main():
 p=argparse.ArgumentParser();p.add_argument('endpoint');p.add_argument('--samples',type=int,default=10);a=p.parse_args();c=JsonRpcClient(a.endpoint,timeout=5);lat=[];fail=[];heads=[]
 for _ in range(a.samples):
  try:r=c.call('eth_blockNumber');lat.append(r.latency_ms);heads.append(int(r.result,16))
  except Exception as e:fail.append(sanitize_text(e))
 out={'endpoint':c.label,'samples':a.samples,'successes':len(lat),'failures':len(fail),'p50_ms':pct(lat,.5),'p90_ms':pct(lat,.9),'p99_ms':pct(lat,.99),'head_min':min(heads) if heads else None,'head_max':max(heads) if heads else None,'errors':fail[:3]};print(json.dumps(out,sort_keys=True));return 0 if lat else 2
if __name__=='__main__':raise SystemExit(main())
