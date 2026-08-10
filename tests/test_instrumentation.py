import pytest
from across_edge.instrumentation import CandidateInstrumentation
from across_edge.model import ShadowRecord
from across_edge.storage import Store
def rec():return ShadowRecord(4,'r','1:1',1,1,42161,'i','o',1,1,'',0,'open',trace_id='t')
def test_strict_sequence_includes_actionable_gate(tmp_path):
 s=Store(tmp_path/'i.db');i=CandidateInstrumentation(s);r=rec()
 for n,stage in enumerate(('T0','TA','T1','T2','T3'),1):i.mark(r,stage,at_ns=n*10)
 row=s.shadow_by_trace('r','t');assert [row[x] for x in ('t0_monotonic_ns','ta_monotonic_ns','t1_monotonic_ns','t2_monotonic_ns','t3_monotonic_ns')]==[10,20,30,40,50];s.close()
@pytest.mark.parametrize('stage',('TA','T1','T2','T3'))
def test_cannot_skip_prerequisite(tmp_path,stage):
 s=Store(tmp_path/'i.db');i=CandidateInstrumentation(s);r=rec()
 with pytest.raises(RuntimeError,match='out-of-order'):i.mark(r,stage,at_ns=10)
 s.close()
def test_cannot_overwrite_or_go_backwards(tmp_path):
 s=Store(tmp_path/'i.db');i=CandidateInstrumentation(s);r=rec();i.mark(r,'T0',at_ns=20)
 with pytest.raises(RuntimeError,match='overwrite'):i.mark(r,'T0',at_ns=21)
 with pytest.raises(RuntimeError,match='non-monotonic'):i.mark(r,'TA',at_ns=19)
 s.close()
