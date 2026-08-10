from __future__ import annotations
from collections import defaultdict
from statistics import median
from time import perf_counter_ns
from datetime import datetime,timezone
from .classification import classify_candidate
from .model import DepositEvent,FillEvent,ShadowRecord
from .storage import Store

def utc_now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def percentile(values,p):
    if not values:return None
    xs=sorted(values);return xs[int(round((len(xs)-1)*p))]
class Observer:
    def __init__(self,store:Store,relayer_address:str|None=None):self.store=store;self.relayer_address=relayer_address
    def ingest_deposit(self,d:DepositEvent,run_id:str,*,destination_time:int|None=None,trace_id:str|None=None)->ShadowRecord:
        self.store.upsert_deposit(d);trace_id=trace_id or f'{d.key}:observer'
        rows=self.store.shadow_for_deposit(run_id,d.key)
        existing=next((x for x in rows if x.get('trace_id')==trace_id),None)
        if existing:r=ShadowRecord(**existing)
        else:
            initial_state='other' if destination_time is None else classify_candidate(d,self.relayer_address,destination_time)
            r=ShadowRecord(2,run_id,d.key,d.origin_chain_id,d.deposit_id,d.destination_chain_id,d.input_token,d.output_token,d.input_amount,d.output_amount,d.exclusive_relayer,d.exclusivity_deadline,initial_state,trace_id=trace_id,decision_destination_time=destination_time)
        if destination_time is not None:self._transition(r,d,destination_time)
        self.store.upsert_shadow(r);return r
    def _transition(self,r:ShadowRecord,d:DepositEvent,destination_time:int):
        state=classify_candidate(d,self.relayer_address,destination_time)
        allowed={("other","open"),("other","exclusive_other"),("other","exclusive_self"),("other","step_in"),("exclusive_other","step_in"),("exclusive_self","step_in"),("open","open"),("step_in","step_in"),("exclusive_other","exclusive_other"),("exclusive_self","exclusive_self")}
        if r.candidate_type!=state and (r.candidate_type,state) not in allowed:raise RuntimeError(f'invalid candidate state transition {r.candidate_type}->{state}')
        r.candidate_type=state;r.decision_destination_time=destination_time
        if self.store.add_transition(r.run_id,r.trace_id,state,destination_time):r.candidate_state_history=self.store.transitions(r.run_id,r.trace_id)
    def refresh_candidate_states(self,run_id:str,destination_chain_id:int,destination_time:int):
        deps={f"{d['origin_chain_id']}:{d['deposit_id']}":DepositEvent(**d) for d in self.store.all_deposits() if d['destination_chain_id']==destination_chain_id}
        for row in self.store.shadow_rows(run_id):
            if row['deposit_key'] in deps:
                r=ShadowRecord(**row);self._transition(r,deps[row['deposit_key']],destination_time);self.store.upsert_shadow(r)
    def ingest_fill(self,f:FillEvent,run_id:str,*,observed_monotonic_ns:int|None=None,observed_wall_utc:str|None=None)->bool:
        inserted=self.store.insert_fill(f)
        if not inserted:return False
        rows=self.store.shadow_for_deposit(run_id,f.key)
        for data in rows:
            if data.get('winner_tx_hash'):continue
            data['winner_relayer']=f.relayer;data['winner_tx_hash']=f.tx_hash;data['winner_block']=f.block_number
            data['tw_monotonic_ns']=perf_counter_ns() if observed_monotonic_ns is None else observed_monotonic_ns;data['tw_wall_utc']=utc_now() if observed_wall_utc is None else observed_wall_utc
            if data.get('t3_monotonic_ns') is not None:data['shadow_headroom_ms']=(data['tw_monotonic_ns']-data['t3_monotonic_ns'])/1_000_000
            dep=next((d for d in self.store.all_deposits() if f"{d['origin_chain_id']}:{d['deposit_id']}"==f.key),None)
            if dep:data['winner_latency_ms']=max(0.0,(f.block_timestamp-dep['block_timestamp'])*1000.0)
            self.store.upsert_shadow(ShadowRecord(**data))
        return True

def competitor_scoreboard(deposits,fills):
    deps={f"{d['origin_chain_id']}:{d['deposit_id']}":d for d in deposits};grouped=defaultdict(list)
    for f in fills:
        k=f"{f['origin_chain_id']}:{f['deposit_id']}"
        if k in deps:grouped[f['relayer'].lower()].append((deps[k],f))
    out=[]
    for relayer,pairs in grouped.items():
        lat=[max(0.0,(f['block_timestamp']-d['block_timestamp'])*1000.0) for d,f in pairs]
        out.append({'relayer':relayer,'fills_observed':len(pairs),'median_deposit_to_fill_ms':median(lat),'p10_ms':percentile(lat,.1),'p90_ms':percentile(lat,.9),'routes':sorted({f"{d['origin_chain_id']}->{d['destination_chain_id']}" for d,_ in pairs})})
    return sorted(out,key=lambda x:(-x['fills_observed'],x['relayer']))
