import time
from across_edge.model import ShadowRecord
from across_edge.storage import Store
def test_direct_trace_lookup_does_not_depend_on_shadow_rows(monkeypatch,tmp_path):
 s=Store(tmp_path/'x');s.upsert_shadow(ShadowRecord(3,'r','1:1',1,1,8453,'i','o',1,1,'',0,'open',trace_id='target'));monkeypatch.setattr(s,'shadow_rows',lambda *_:(_ for _ in ()).throw(AssertionError('full scan')));assert s.shadow_by_trace('r','target')['trace_id']=='target';s.close()
def test_direct_lookup_at_representative_count(tmp_path):
 s=Store(tmp_path/'x')
 for i in range(2000):s.upsert_shadow(ShadowRecord(3,'r',f'1:{i}',1,i,8453,'i','o',1,1,'',0,'open',trace_id=f't{i}'),commit=False)
 s.db.commit();samples=[]
 for _ in range(100):
  a=time.perf_counter_ns();assert s.shadow_by_trace('r','t1999');samples.append(time.perf_counter_ns()-a)
 assert sorted(samples)[89]<20_000_000;s.close()
