from __future__ import annotations
from datetime import datetime,timezone
from time import perf_counter_ns
from .model import ShadowRecord
from .storage import Store
FIELDS={'T0':'t0_monotonic_ns','TA':'ta_monotonic_ns','T1':'t1_monotonic_ns','T2':'t2_monotonic_ns','T3':'t3_monotonic_ns'}
WALL={'T0':'t0_wall_utc','TA':'ta_wall_utc','T1':'t1_wall_utc','T2':'t2_wall_utc','T3':'t3_wall_utc'}
ORDER=('T0','TA','T1','T2','T3')
def utc_now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
class CandidateInstrumentation:
    def __init__(self,store:Store):self.store=store
    def mark(self,record:ShadowRecord,stage:str,*,at_ns:int|None=None,wall_utc:str|None=None,correction:bool=False,**updates)->ShadowRecord:
        if stage not in FIELDS:raise ValueError(stage)
        idx=ORDER.index(stage);current=[getattr(record,FIELDS[s]) for s in ORDER]
        if current[idx] is not None and not correction:raise RuntimeError(f'stage overwrite prohibited: {stage}')
        if not correction:
            if idx and current[idx-1] is None:raise RuntimeError(f'out-of-order stage: {stage}')
            if any(v is not None for v in current[idx+1:]):raise RuntimeError(f'out-of-order stage: {stage}')
        now=perf_counter_ns() if at_ns is None else at_ns
        prior=[v for v in current[:idx] if v is not None]
        if prior and now<prior[-1]:raise RuntimeError('non-monotonic candidate stage')
        setattr(record,FIELDS[stage],now);setattr(record,WALL[stage],wall_utc or utc_now())
        for k,v in updates.items():
            if not hasattr(record,k):raise AttributeError(k)
            setattr(record,k,v)
        self.store.upsert_shadow(record);return record
