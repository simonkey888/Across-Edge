from __future__ import annotations
import json
from time import perf_counter_ns
from .instrumentation import CandidateInstrumentation
from .model import ShadowRecord
from .observer import Observer
from .storage import Store
PREFIX='ACROSS_EDGE_EVENT '
class UpstreamEventError(RuntimeError):pass
class ShadowCoordinator:
    def __init__(self,store:Store,run_id:str):self.store=store;self.run_id=run_id;self.inst=CandidateInstrumentation(store);self.observer=Observer(store)
    def parse_line(self,line:str)->dict|None:
        if not line.startswith(PREFIX):return None
        obj=json.loads(line[len(PREFIX):]);stage=obj.get('stage')
        if stage not in {'T0','TA','T1','T2','T3'}:raise UpstreamEventError('invalid stage')
        if obj.get('version')!=3:raise UpstreamEventError('unsupported upstream instrumentation version')
        return obj
    def ingest_line(self,line:str,*,at_ns:int|None=None)->ShadowRecord|None:
        received_ns=perf_counter_ns() if at_ns is None else at_ns
        e=self.parse_line(line)
        if e is None:return None
        trace=str(e['trace_id']);row=self.store.shadow_by_trace(self.run_id,trace)
        if row:r=ShadowRecord(**row)
        else:
            if e['stage']!='T0':raise UpstreamEventError('first event must be T0')
            r=ShadowRecord(3,self.run_id,str(e['deposit_key']),int(e['origin_chain_id']),int(e['deposit_id']),int(e['destination_chain_id']),str(e.get('input_token','')),str(e.get('output_token','')),int(e.get('input_amount',0)),int(e.get('output_amount',0)),str(e.get('exclusive_relayer','')),int(e.get('exclusivity_deadline',0)),str(e.get('candidate_type','other')),trace_id=trace,deposit_block=int(e.get('deposit_block',0)) if e.get('deposit_block') is not None else None)
        source=dict(r.source_stage_monotonic_ns);source[e['stage']]=str(e.get('source_monotonic_ns',''));r.source_stage_monotonic_ns=source
        updates={}
        for key in ('eligible','profitability_decision','simulation_result','transaction_ready','rejection_reason','transaction_serialized','decision_destination_time','deposit_block','max_block_number','live_equivalent_confirmations_satisfied','simulation_early_not_live_actionable','first_actionable_destination_time'):
            if key in e:updates[key]=e[key]
        if 'economics' in e:updates['economics']=e['economics'];updates['evidence_classes']={k:'OBSERVED_THIS_RUN' for k in e['economics']}
        stage_field={'T0':'t0_monotonic_ns','TA':'ta_monotonic_ns','T1':'t1_monotonic_ns','T2':'t2_monotonic_ns','T3':'t3_monotonic_ns'}[e['stage']]
        if getattr(r,stage_field) is not None:
            for k,v in updates.items():setattr(r,k,v)
            self.store.upsert_shadow(r);self.observer.reconcile_deposit(self.run_id,r.deposit_key);return r
        result=self.inst.mark(r,e['stage'],at_ns=received_ns,wall_utc=e.get('wall_utc'),**updates)
        if e['stage'] in {'T0','T3'}:self.observer.reconcile_deposit(self.run_id,result.deposit_key)
        return result
