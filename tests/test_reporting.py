from across_edge.model import ShadowRecord
from across_edge.reporting import build_report
from across_edge.storage import Store
def test_schema_3_unknowns_and_ta_business_baseline(tmp_path):
 s=Store(tmp_path/'x');s.upsert_shadow(ShadowRecord(3,'r','1:1',1,1,8453,'i','o',1,1,'',0,'open',trace_id='a',t0_monotonic_ns=10,simulation_early_not_live_actionable=True));s.upsert_shadow(ShadowRecord(3,'r','1:2',1,2,8453,'i','o',1,1,'',0,'open',trace_id='b',t0_monotonic_ns=10,ta_monotonic_ns=20,t1_monotonic_ns=30,t2_monotonic_ns=40,t3_monotonic_ns=50,live_equivalent_confirmations_satisfied=True,eligible=True,profitability_decision='profitable',transaction_ready=True));r=build_report(s,'r');assert r['schema_version']==3 and r['raw_candidates']==2 and r['live_equivalent_actionable_candidates']==1 and r['eligible_opportunities']==1 and r['ta_t1_p50_ms']==.00001 and r['ready_before_winner_pct'] is None;s.close()
