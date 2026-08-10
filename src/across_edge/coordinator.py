from __future__ import annotations
import json
from time import perf_counter_ns
from .instrumentation import CandidateInstrumentation
from .model import ShadowRecord
from .observer import Observer
from .storage import Store
from .versioning import deposit_version_identity
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
    def _new_attempt(self,e,received_ns):
        upstream_trace=str(e['trace_id']);previous=self.store.db.execute('SELECT COUNT(*) AS n FROM evaluation_attempts WHERE run_id=? AND upstream_trace_id=?',(self.run_id,upstream_trace)).fetchone()['n'];attempt_id=upstream_trace if previous==0 else f"{upstream_trace}:attempt:{received_ns}"
        version_id,fp,provenance,fields=deposit_version_identity(e,attempt_id);key=str(e['deposit_key']);self.store.create_version(self.run_id,key,version_id,fp,provenance,fields)
        r=ShadowRecord(3,self.run_id,key,int(e['origin_chain_id']),int(e['deposit_id']),int(e['destination_chain_id']),str(e.get('input_token','')),str(e.get('output_token','')),int(e.get('input_amount',0)),int(e.get('output_amount',0)),str(e.get('exclusive_relayer','')),int(e.get('exclusivity_deadline',0)),str(e.get('candidate_type','other')),trace_id=attempt_id,evaluation_attempt_id=attempt_id,upstream_trace_id=upstream_trace,deposit_version_id=version_id,deposit_version_fingerprint=fp,deposit_version_provenance=provenance,deposit_block=int(e.get('deposit_block',0)) if e.get('deposit_block') is not None else None)
        self.store.create_attempt(self.run_id,attempt_id,upstream_trace,key,version_id,received_ns,e);self.store.link_deposit(self.run_id,key,True,version_id=version_id,payload=e);return r
    def ingest_line(self,line:str,*,at_ns:int|None=None)->ShadowRecord|None:
        received_ns=perf_counter_ns() if at_ns is None else at_ns;e=self.parse_line(line)
        if e is None:return None
        upstream_trace=str(e['trace_id'])
        if e['stage']=='T0':
            active=self.store.active_attempt(self.run_id,upstream_trace)
            if active and self.store.shadow_by_trace(self.run_id,active) and self.store.shadow_by_trace(self.run_id,active).get('t0_monotonic_ns') is not None:self.store.db.execute('DELETE FROM active_attempts WHERE run_id=? AND upstream_trace_id=?',(self.run_id,upstream_trace));self.store.db.commit()
            r=self._new_attempt(e,received_ns)
        else:
            attempt_id=self.store.active_attempt(self.run_id,upstream_trace)
            if not attempt_id:raise UpstreamEventError('stage has no active evaluation attempt')
            row=self.store.shadow_by_trace(self.run_id,attempt_id)
            if not row:raise UpstreamEventError('active evaluation attempt record missing')
            r=ShadowRecord(**row)
        source=dict(r.source_stage_monotonic_ns);source[e['stage']]=str(e.get('source_monotonic_ns',''));r.source_stage_monotonic_ns=source
        updates={k:e[k] for k in ('eligible','profitability_decision','simulation_result','transaction_ready','rejection_reason','transaction_serialized','decision_destination_time','deposit_block','max_block_number','live_equivalent_confirmations_satisfied','simulation_early_not_live_actionable','first_actionable_destination_time') if k in e}
        if 'economics' in e:updates['economics']=e['economics'];updates['evidence_classes']={k:'OBSERVED_THIS_RUN' for k in e['economics']}
        wall=e.get('wall_utc')
        if not self.store.record_attempt_stage(self.run_id,r.evaluation_attempt_id,e['stage'],received_ns,wall or '',e):return r
        result=self.inst.mark(r,e['stage'],at_ns=received_ns,wall_utc=wall,**updates);agg=self.store.aggregate(self.run_id,r.deposit_key)
        if e['stage']=='TA' and not (agg and agg.get('first_actionable_attempt_id')):self.store.set_aggregate(self.run_id,r.deposit_key,first_actionable_attempt_id=r.evaluation_attempt_id)
        if e['stage']=='T1':self.store.set_aggregate(self.run_id,r.deposit_key,current_decision_attempt_id=r.evaluation_attempt_id)
        if e['stage']=='T3' and result.transaction_ready is True and not (agg and agg.get('first_ready_attempt_id')):self.store.set_aggregate(self.run_id,r.deposit_key,first_ready_attempt_id=r.evaluation_attempt_id)
        if e['stage'] in {'T0','T3'}:self.observer.reconcile_deposit(self.run_id,result.deposit_key)
        return result
