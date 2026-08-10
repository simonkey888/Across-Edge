from collections import defaultdict
from statistics import median
from time import perf_counter_ns
from datetime import datetime, timezone
from .classification import classify_candidate
from .model import DepositEvent,FillEvent,ShadowRecord
from .storage import Store

def utc_now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def percentile(values,p):
    if not values:return None
    xs=sorted(values); return xs[int(round((len(xs)-1)*p))]
class Observer:
    def __init__(self,store:Store,relayer_address:str|None=None): self.store=store; self.relayer_address=relayer_address
    def ingest_deposit(self,d:DepositEvent,run_id:str)->ShadowRecord:
        self.store.upsert_deposit(d); r=ShadowRecord(1,run_id,d.key,d.origin_chain_id,d.deposit_id,d.destination_chain_id,d.input_token,d.output_token,d.input_amount,d.output_amount,d.exclusive_relayer,d.exclusivity_deadline,classify_candidate(d,self.relayer_address,d.block_timestamp)); self.store.upsert_shadow(r); return r
    def ingest_fill(self,f:FillEvent,run_id:str,*,observed_monotonic_ns:int|None=None,observed_wall_utc:str|None=None)->bool:
        inserted=self.store.insert_fill(f); rows={r["deposit_key"]:r for r in self.store.shadow_rows(run_id)}
        if f.key not in rows:return inserted
        data=rows[f.key]; data["winner_relayer"]=f.relayer; data["winner_tx_hash"]=f.tx_hash; data["winner_block"]=f.block_number; data["tw_monotonic_ns"]=perf_counter_ns() if observed_monotonic_ns is None else observed_monotonic_ns; data["tw_wall_utc"]=utc_now() if observed_wall_utc is None else observed_wall_utc
        if data.get("t3_monotonic_ns") is not None:data["shadow_headroom_ms"]=(data["tw_monotonic_ns"]-data["t3_monotonic_ns"])/1_000_000
        dep=next((d for d in self.store.all_deposits() if f"{d['origin_chain_id']}:{d['deposit_id']}"==f.key),None)
        if dep:data["winner_latency_ms"]=max(0.0,(f.block_timestamp-dep["block_timestamp"])*1000.0)
        self.store.upsert_shadow(ShadowRecord(**data)); return inserted

def competitor_scoreboard(deposits,fills):
    deps={f"{d['origin_chain_id']}:{d['deposit_id']}":d for d in deposits}; grouped=defaultdict(list)
    for f in fills:
        k=f"{f['origin_chain_id']}:{f['deposit_id']}"
        if k in deps:grouped[f["relayer"].lower()].append((deps[k],f))
    out=[]
    for relayer,pairs in grouped.items():
        lat=[max(0.0,(f["block_timestamp"]-d["block_timestamp"])*1000.0) for d,f in pairs]
        out.append({"relayer":relayer,"fills_observed":len(pairs),"median_deposit_to_fill_ms":median(lat),"p10_ms":percentile(lat,.1),"p90_ms":percentile(lat,.9),"routes":sorted({f"{d['origin_chain_id']}->{d['destination_chain_id']}" for d,_ in pairs})})
    return sorted(out,key=lambda x:(-x["fills_observed"],x["relayer"]))
