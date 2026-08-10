from __future__ import annotations
import json
from time import perf_counter_ns
from .instrumentation import CandidateInstrumentation
from .model import ShadowRecord
from .storage import Store
PREFIX='ACROSS_EDGE_EVENT '
class UpstreamEventError(RuntimeError):pass
class ShadowCoordinator:
    def __init__(self,store:Store,run_id:str):self.store=store;self.run_id=run_id;self.inst=CandidateInstrumentation(store)
    def parse_line(self,line:str)->dict|None:
        if not line.startswith(PREFIX):return None
        obj=json.loads(line[len(PREFIX):]);stage=obj.get('stage')
        if stage not in {'T0','T1','T2','T3'}:raise UpstreamEventError('invalid stage')
        if obj.get('version')!=2:raise UpstreamEventError('unsupported upstream instrumentation version')
        return obj
    def ingest_line(self,line:str,*,at_ns:int|None=None)->ShadowRecord|None:
        e=self.parse_line(line)
        if e is None:return None
        trace=str(e['trace_id']);rows=self.store.shadow_rows(self.run_id);row=next((x for x in rows if x.get('trace_id')==trace),None)
        if row:r=ShadowRecord(**row)
        else:
            if e['stage']!='T0':raise UpstreamEventError('first event must be T0')
            r=ShadowRecord(2,self.run_id,str(e['deposit_key']),int(e['origin_chain_id']),int(e['deposit_id']),int(e['destination_chain_id']),str(e.get('input_token','')),str(e.get('output_token','')),int(e.get('input_amount',0)),int(e.get('output_amount',0)),str(e.get('exclusive_relayer','')),int(e.get('exclusivity_deadline',0)),str(e.get('candidate_type','other')),trace_id=trace)
        updates={}
        for key in ('eligible','profitability_decision','simulation_result','transaction_ready','rejection_reason','transaction_serialized','decision_destination_time'):
            if key in e:updates[key]=e[key]
        if 'economics' in e:updates['economics']=e['economics'];updates['evidence_classes']={k:'OBSERVED_THIS_RUN' for k in e['economics']}
        return self.inst.mark(r,e['stage'],at_ns=perf_counter_ns() if at_ns is None else at_ns,wall_utc=e.get('wall_utc'),**updates)
