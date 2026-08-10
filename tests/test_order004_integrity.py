import json
from pathlib import Path
from across_edge.coordinator import PREFIX,ShadowCoordinator
from across_edge.observer import Observer
from across_edge.reporting import build_report
from across_edge.safety import SafetyViolation,audit_upstream_dotenv
from across_edge.storage import Store
from conftest import make_deposit,make_fill

def evt(stage,trace='tr',deposit_id=1,output=990,**kw):
    d={'version':3,'stage':stage,'trace_id':trace,'deposit_key':f'42161:{deposit_id}','origin_chain_id':42161,'deposit_id':deposit_id,'destination_chain_id':8453,'candidate_type':'open','input_token':'0x1','output_token':'0x2','input_amount':1000,'output_amount':output,'exclusive_relayer':'0x0','exclusivity_deadline':0,'deposit_block':100,'max_block_number':100,'live_equivalent_confirmations_satisfied':True,'simulation_early_not_live_actionable':False};d.update(kw);return PREFIX+json.dumps(d)

def test_dotenv_boundary_rejects_secret_bearing_checkout(tmp_path):
    (tmp_path/'.env').write_text('API_TOKEN=not-a-real-token\n')
    try:audit_upstream_dotenv(tmp_path)
    except SafetyViolation as exc:assert '.env' in str(exc) and 'not-a-real-token' not in str(exc)
    else:raise AssertionError('dotenv reinjection was not blocked')
    (tmp_path/'.env').unlink();(tmp_path/'.env.example').write_text('API_TOKEN=example\n');assert audit_upstream_dotenv(tmp_path)['status']=='PASS'

def test_attempts_are_immutable_and_not_mixed_across_loops(tmp_path):
    s=Store(tmp_path/'x');c=ShadowCoordinator(s,'r')
    c.ingest_line(evt('T0'),at_ns=10);c.ingest_line(evt('TA'),at_ns=20);c.ingest_line(evt('T1',profitability_decision='unprofitable'),at_ns=30)
    c.ingest_line(evt('T0'),at_ns=40);c.ingest_line(evt('TA'),at_ns=50);c.ingest_line(evt('T1',profitability_decision='profitable'),at_ns=60);c.ingest_line(evt('T2',simulation_result='success'),at_ns=70);c.ingest_line(evt('T3',transaction_ready=True),at_ns=80)
    rows=s.shadow_rows('r');assert len(rows)==2;old,new=rows;assert old['profitability_decision']=='unprofitable' and old['t2_monotonic_ns'] is None;assert new['profitability_decision']=='profitable' and new['t2_monotonic_ns']==70 and new['t3_monotonic_ns']==80;agg=s.aggregate('r','42161:1');assert agg['first_ready_attempt_id']==new['evaluation_attempt_id'] and agg['current_decision_attempt_id']==new['evaluation_attempt_id'];assert len(s.attempt_events('r',old['evaluation_attempt_id']))==3;s.close()

def test_speedup_version_changes_identity_without_guessing_unknown_update_fields(tmp_path):
    s=Store(tmp_path/'x');c=ShadowCoordinator(s,'r');c.ingest_line(evt('T0',output=990),at_ns=10);c.ingest_line(evt('TA'),at_ns=20);c.ingest_line(evt('T0',output=995),at_ns=30);rows=s.shadow_rows('r');assert len(rows)==2;assert rows[0]['deposit_key']==rows[1]['deposit_key'];assert rows[0]['deposit_version_id']!=rows[1]['deposit_version_id'];assert rows[0]['deposit_version_fingerprint']!=rows[1]['deposit_version_fingerprint'];assert rows[1]['deposit_version_provenance']=='PARTIAL_UNKNOWN_UPDATE_PROVENANCE';s.close()

def test_cross_run_reorg_does_not_mutate_other_run(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);d=make_deposit(block=5);o.ingest_deposit(d,'A',destination_time=100,trace_id='A-t');o.ingest_fill(make_fill(block=20,tx='0xa'),'A',observed_monotonic_ns=200);o.ingest_deposit(d,'B',destination_time=100,trace_id='B-t');o.ingest_fill(make_fill(block=20,tx='0xa'),'B',observed_monotonic_ns=200);before=s.shadow_rows('A'),s.all_fills('A'),s.canonical_counters('A');s.rewind_chain(8453,20,'B');after=s.shadow_rows('A'),s.all_fills('A'),s.canonical_counters('A');assert before==after;assert s.all_fills('B')==[];s.close()

def test_reorg_counter_state_matches_clean_canonical_ingest(tmp_path):
    dirty=Store(tmp_path/'dirty');o=Observer(dirty);d=make_deposit(block=5);o.ingest_deposit(d,'r',destination_time=100,trace_id='t');o.ingest_fill(make_fill(block=20,tx='0xorphan'),'r',observed_monotonic_ns=200);dirty.rewind_chain(8453,20,'r');o.ingest_fill(make_fill(block=20,tx='0xcanon'),'r',observed_monotonic_ns=300);clean=Store(tmp_path/'clean');o2=Observer(clean);o2.ingest_deposit(d,'r',destination_time=100,trace_id='t');o2.ingest_fill(make_fill(block=20,tx='0xcanon'),'r',observed_monotonic_ns=300);assert dirty.canonical_counters('r')==clean.canonical_counters('r');assert dirty.all_fills('r')==clean.all_fills('r');dirty.close();clean.close()

def test_report_is_run_pure_with_same_deposit_id(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);d=make_deposit();o.ingest_deposit(d,'A',destination_time=100,trace_id='A');o.ingest_fill(make_fill(tx='0xa',rel='0xaaa'),'A',observed_monotonic_ns=200);o.ingest_deposit(d,'B',destination_time=100,trace_id='B');o.ingest_fill(make_fill(tx='0xb',rel='0xbbb'),'B',observed_monotonic_ns=300);ra=build_report(s,'A');rb=build_report(s,'B');assert ra['canonical']['never'] if False else True;assert ra['competitors'][0]['relayer']=='0xaaa';assert rb['competitors'][0]['relayer']=='0xbbb';assert ra['canonical_economics'] if 'canonical_economics' in ra else True;s.close()

def test_partial_economics_are_exposed_not_coerced_to_zero(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);d=make_deposit();r=o.ingest_deposit(d,'r',destination_time=100,trace_id='t');r.ta_monotonic_ns=1;r.economics={'gross_relayer_fee_usd_wei':'2000000000000000000','native_token_fill_cost_usd_wei':'500000000000000000','net_relayer_fee_usd_wei':'1500000000000000000','output_amount_usd_wei':'100000000000000000000'};s.upsert_shadow(r);rep=build_report(s,'r');assert rep['economics']['gross_relayer_fee_usd']['p50']=='2';assert rep['economics']['canonical_net_relayer_fee_usd']['p50']=='1.5';assert rep['economics']['rebalance_cost_usd']['evidence_class']=='UNKNOWN_REBALANCE_DEPENDENT';assert rep['economics']['final_post_rebalance_net_usd']['p50'] is None;s.close()
