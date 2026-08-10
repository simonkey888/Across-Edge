import json,time
from across_edge.coordinator import ShadowCoordinator,PREFIX
from across_edge.storage import Store
def evt(stage,**kw):
 d={'version':3,'stage':stage,'trace_id':'tr','deposit_key':'42161:1','origin_chain_id':42161,'deposit_id':1,'destination_chain_id':8453,'candidate_type':'other','deposit_block':100,'wall_utc':'2026-08-10T00:00:00Z','source_monotonic_ns':'999'};d.update(kw);return PREFIX+json.dumps(d)
def test_early_simulation_becomes_actionable_at_threshold_and_survives_restart(tmp_path):
 path=tmp_path/'x.db';s=Store(path);c=ShadowCoordinator(s,'r');c.ingest_line(evt('T0',max_block_number=99,live_equivalent_confirmations_satisfied=False,simulation_early_not_live_actionable=True),at_ns=10);r=s.shadow_by_trace('r','tr');assert r['ta_monotonic_ns'] is None and r['simulation_early_not_live_actionable']
 c.ingest_line(evt('T0',max_block_number=100,live_equivalent_confirmations_satisfied=True,simulation_early_not_live_actionable=False),at_ns=15);c.ingest_line(evt('TA',max_block_number=100,live_equivalent_confirmations_satisfied=True,first_actionable_destination_time=200),at_ns=20);s.close();s=Store(path);r=s.shadow_by_trace('r','tr');assert r['t0_monotonic_ns']==10 and r['ta_monotonic_ns']==20 and r['max_block_number']==100;s.close()
def test_zero_confirmation_case_can_be_actionable_at_deposit_block(tmp_path):
 s=Store(tmp_path/'x.db');c=ShadowCoordinator(s,'r');c.ingest_line(evt('T0',max_block_number=100,live_equivalent_confirmations_satisfied=True),at_ns=10);c.ingest_line(evt('TA',max_block_number=100,live_equivalent_confirmations_satisfied=True),at_ns=11);assert s.shadow_by_trace('r','tr')['ta_monotonic_ns']==11;s.close()
def test_receive_timestamp_is_captured_before_parse(monkeypatch,tmp_path):
 s=Store(tmp_path/'x.db');c=ShadowCoordinator(s,'r');orig=c.parse_line
 def slow(line):time.sleep(.015);return orig(line)
 monkeypatch.setattr(c,'parse_line',slow);before=time.perf_counter_ns();c.ingest_line(evt('T0',live_equivalent_confirmations_satisfied=False));after=time.perf_counter_ns();t=s.shadow_by_trace('r','tr')['t0_monotonic_ns'];assert before<=t<after-5_000_000;s.close()
def test_duplicate_loop_events_do_not_rewrite_stage_time(tmp_path):
 s=Store(tmp_path/'x.db');c=ShadowCoordinator(s,'r');c.ingest_line(evt('T0',max_block_number=99),at_ns=10);c.ingest_line(evt('T0',max_block_number=100),at_ns=99);assert s.shadow_by_trace('r','tr')['t0_monotonic_ns']==10;s.close()
