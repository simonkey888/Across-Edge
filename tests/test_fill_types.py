import pytest
from across_edge.observer import Observer
from across_edge.reporting import build_report
from across_edge.storage import Store
from conftest import make_deposit,make_fill
@pytest.mark.parametrize('value,name,competitive',[(0,'FastFill',True),(1,'ReplacedSlowFill',True),(2,'SlowFill',False),(9,'UNKNOWN_9',False)])
def test_fill_type_classification(value,name,competitive):
 f=make_fill(fill_type=value);assert f.fill_type_name==name and f.competitive is competitive
def test_slow_and_unknown_do_not_contaminate_competitor_metrics(tmp_path):
 s=Store(tmp_path/'x');o=Observer(s);o.ingest_deposit(make_deposit(),'r',destination_time=100,trace_id='t');o.ingest_fill(make_fill(tx='0xslow',block=11,fill_type=2),'r',observed_monotonic_ns=150);o.ingest_fill(make_fill(tx='0xfast',block=12,fill_type=0),'r',observed_monotonic_ns=200);o.ingest_fill(make_fill(tx='0xunknown',block=10,fill_type=9),'r',observed_monotonic_ns=140);row=s.shadow_by_trace('r','t');assert row['winner_tx_hash']=='0xfast' and row['winner_fill_type']==0;rep=build_report(s,'r');assert rep['slow_fill_count']==1 and rep['unknown_fill_type_count']==1 and not rep['competitiveness_metrics_complete'];assert rep['competitors'][0]['fills_observed']==1;s.close()
