from __future__ import annotations
from datetime import datetime, timezone
from time import perf_counter_ns
from .model import ShadowRecord
from .storage import Store
FIELDS={"T0":"t0_monotonic_ns","T1":"t1_monotonic_ns","T2":"t2_monotonic_ns","T3":"t3_monotonic_ns"}
def utc_now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
class CandidateInstrumentation:
    def __init__(self,store:Store): self.store=store
    def mark(self,record:ShadowRecord,stage:str,*,at_ns:int|None=None,**updates)->ShadowRecord:
        if stage not in FIELDS: raise ValueError(stage)
        now=perf_counter_ns() if at_ns is None else at_ns
        prior=[getattr(record,FIELDS[s]) for s in ("T0","T1","T2","T3") if getattr(record,FIELDS[s]) is not None]
        if prior and now<prior[-1]: raise RuntimeError("non-monotonic candidate stage")
        setattr(record,FIELDS[stage],now)
        if stage=="T0" and record.t0_wall_utc is None: record.t0_wall_utc=utc_now()
        for k,v in updates.items():
            if not hasattr(record,k): raise AttributeError(k)
            setattr(record,k,v)
        self.store.upsert_shadow(record); return record
