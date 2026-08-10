import pytest
from across_edge.instrumentation import CandidateInstrumentation
from across_edge.model import ShadowRecord
from across_edge.storage import Store
def rec():return ShadowRecord(2,'r','1:1',1,1,42161,'i','o',1,1,'',0,'open',trace_id='t')
def test_strict_sequence_and_persistence(tmp_path):
 s=Store(tmp_path/'i.db');i=CandidateInstrumentation(s);r=rec()
 for n,stage in enumerate(('T0','T1','T2','T3'),1):i.mark(r,stage,at_ns=n*10)
 row=s.shadow_rows('r')[0];assert [row[f't{x}_monotonic_ns'] for x in range(4)]==[10,20,30,40];s.close()
@pytest.mark.parametrize('stage',('T1','T2','T3'))
def test_cannot_skip_stage(tmp_path,stage):
 s=Store(tmp_path/'i.db');i=CandidateInstrumentation(s);r=rec()
 with pytest.raises(RuntimeError,match='out-of-order'):i.mark(r,stage,at_ns=10)
 s.close()
def test_cannot_overwrite_or_go_backwards(tmp_path):
 s=Store(tmp_path/'i.db');i=CandidateInstrumentation(s);r=rec();i.mark(r,'T0',at_ns=20)
 with pytest.raises(RuntimeError,match='overwrite'):i.mark(r,'T0',at_ns=21)
 with pytest.raises(RuntimeError,match='non-monotonic'):i.mark(r,'T1',at_ns=19)
 s.close()
