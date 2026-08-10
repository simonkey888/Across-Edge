from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
from statistics import median
from time import perf_counter_ns
from .classification import classify_candidate
from .model import COMPETITIVE_FILL_TYPES,FILL_TYPE_NAMES,DepositEvent,FillEvent,ShadowRecord
from .storage import Store
from .versioning import deposit_version_identity

def utc_now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def percentile(values,p):
    if not values:return None
    xs=sorted(values);return xs[int(round((len(xs)-1)*p))]
def competitive_fill(fill:dict)->bool:return int(fill.get('fill_type',-1)) in COMPETITIVE_FILL_TYPES
def fill_type_counts(fills:list[dict])->dict[str,int]:
    c=Counter(FILL_TYPE_NAMES.get(int(f.get('fill_type',-1)),f"UNKNOWN_{f.get('fill_type')}") for f in fills);return dict(sorted(c.items()))
class Observer:
    def __init__(self,store:Store,relayer_address:str|None=None):self.store=store;self.relayer_address=relayer_address
    def ingest_deposit(self,d:DepositEvent,run_id:str,*,destination_time:int|None=None,trace_id:str|None=None,source_block_number:int|None=None,source_block_hash:str|None=None)->ShadowRecord:
        self.store.upsert_deposit(d);trace_id=trace_id or f'{d.key}:observer';existing=self.store.shadow_by_trace(run_id,trace_id)
        if existing:r=ShadowRecord(**existing);version_id=r.deposit_version_id
        else:
            version_id,fp,prov,fields=deposit_version_identity({'origin_chain_id':d.origin_chain_id,'destination_chain_id':d.destination_chain_id,'deposit_id':d.deposit_id,'input_token':d.input_token,'output_token':d.output_token,'input_amount':d.input_amount,'output_amount':d.output_amount,'recipient':d.recipient,'exclusive_relayer':d.exclusive_relayer,'exclusivity_deadline':d.exclusivity_deadline,'fill_deadline':d.fill_deadline},trace_id);self.store.create_version(run_id,d.key,version_id,fp,prov,fields)
            initial='other' if destination_time is None else classify_candidate(d,self.relayer_address,destination_time);r=ShadowRecord(3,run_id,d.key,d.origin_chain_id,d.deposit_id,d.destination_chain_id,d.input_token,d.output_token,d.input_amount,d.output_amount,d.exclusive_relayer,d.exclusivity_deadline,initial,trace_id=trace_id,deposit_version_id=version_id,deposit_version_fingerprint=fp,deposit_version_provenance=prov,decision_destination_time=destination_time,deposit_block=d.block_number)
        self.store.link_deposit(run_id,d.key,True,version_id=version_id,payload=d.__dict__)
        if destination_time is not None:self._transition(r,d,destination_time,source_chain_id=d.destination_chain_id,source_block_number=source_block_number,source_block_hash=source_block_hash)
        self.store.upsert_shadow(r);self.reconcile_deposit(run_id,d.key);return ShadowRecord(**(self.store.shadow_by_trace(run_id,trace_id) or r.as_dict()))
    def _transition(self,r,d,destination_time,*,source_chain_id=None,source_block_number=None,source_block_hash=None):
        state=classify_candidate(d,self.relayer_address,destination_time);allowed={('other','open'),('other','exclusive_other'),('other','exclusive_self'),('other','step_in'),('exclusive_other','step_in'),('exclusive_self','step_in'),('open','open'),('step_in','step_in'),('exclusive_other','exclusive_other'),('exclusive_self','exclusive_self')}
        if r.candidate_type!=state and (r.candidate_type,state) not in allowed:raise RuntimeError(f'invalid candidate state transition {r.candidate_type}->{state}')
        r.candidate_type=state;r.decision_destination_time=destination_time
        if self.store.add_transition(r.run_id,r.trace_id,state,destination_time,source_chain_id=source_chain_id,source_block_number=source_block_number,source_block_hash=source_block_hash):r.candidate_state_history=self.store.transitions(r.run_id,r.trace_id)
    def refresh_candidate_states(self,run_id,destination_chain_id,destination_time,*,source_block_number=None,source_block_hash=None):
        deps={f"{d['origin_chain_id']}:{d['deposit_id']":DepositEvent(**d) for d in self.store.all_deposits(run_id) if d['destination_chain_id']==destination_chain_id}
        for row in self.store.shadow_rows(run_id):
            d=deps.get(row['deposit_key'])
            if d:
                r=ShadowRecord(**row);self._transition(r,d,destination_time,source_chain_id=destination_chain_id,source_block_number=source_block_number,source_block_hash=source_block_hash);self.store.upsert_shadow(r)
    def ingest_fill(self,f:FillEvent,run_id:str,*,observed_monotonic_ns=None,observed_wall_utc=None)->bool:
        now=perf_counter_ns() if observed_monotonic_ns is None else observed_monotonic_ns;wall=utc_now() if observed_wall_utc is None else observed_wall_utc;observed=f.with_observation(now,wall);inserted=self.store.insert_fill(observed);self.store.link_fill(run_id,f.event_id,True)
        if inserted:self.reconcile_deposit(run_id,f.key)
        return inserted
    def reconcile_deposit(self,run_id,key):
        rows=self.store.shadow_for_deposit(run_id,key)
        if not rows:return
        fills=self.store.fills_for_deposit(key,run_id);winner=next((f for f in fills if competitive_fill(f)),None);dep=self.store.deposit_for_run(run_id,key)
        for data in rows:
            for k,v in {'winner_relayer':'','winner_tx_hash':'','winner_block':None,'winner_log_index':None,'winner_fill_type':None,'winner_deposit_version_id':None,'tw_wall_utc':None,'tw_monotonic_ns':None,'winner_latency_ms':None,'shadow_headroom_ms':None}.items():data[k]=v
            if winner:
                data.update(winner_relayer=winner['relayer'],winner_tx_hash=winner['tx_hash'],winner_block=winner['block_number'],winner_log_index=winner.get('log_index'),winner_fill_type=winner.get('fill_type'),winner_deposit_version_id=winner.get('deposit_version_id'),tw_monotonic_ns=winner.get('observed_monotonic_ns'),tw_wall_utc=winner.get('observed_wall_utc'))
                if data.get('t3_monotonic_ns') is not None and data.get('ta_monotonic_ns') is not None and data['tw_monotonic_ns'] is not None:data['shadow_headroom_ms']=(data['tw_monotonic_ns']-data['t3_monotonic_ns'])/1_000_000
                if dep:data['winner_latency_ms']=max(0.0,(winner['block_timestamp']-dep['block_timestamp'])*1000.0)
            self.store.upsert_shadow(ShadowRecord(**data))
def competitor_scoreboard(deposits,fills,*,competitive_only=True):
    deps={f"{d['origin_chain_id']}:{d['deposit_id']}":d for d in deposits};grouped=defaultdict(list)
    for f in fills:
        if competitive_only and not competitive_fill(f):continue
        k=f"{f['origin_chain_id']}:{f['deposit_id']}"
        if k in deps:grouped[f['relayer'].lower()].append((deps[k],f))
    out=[]
    for relayer,pairs in grouped.items():
        lat=[max(0.0,(f['block_timestamp']-d['block_timestamp'])*1000.0) for d,f in pairs];out.append({'relayer':relayer,'fills_observed':len(pairs),'median_deposit_to_fill_ms':median(lat),'p10_ms':percentile(lat,.1),'p90_ms':percentile(lat,.9),'routes':sorted({f"{d['origin_chain_id']}->{d['destination_chain_id']}" for d,_ in pairs}),'fill_types':fill_type_counts([f for _,f in pairs])})
    return sorted(out,key=lambda x:(-x['fills_observed'],x['relayer']))
