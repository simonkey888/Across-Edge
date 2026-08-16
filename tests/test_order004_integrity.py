import json
import subprocess
from pathlib import Path
from across_edge.coordinator import PREFIX,ShadowCoordinator
from across_edge.observer import Observer
from across_edge.reporting import build_report
from across_edge.safety import SafetyViolation,audit_upstream_dotenv
from across_edge.storage import Store
from across_edge.upstream import run_shadow_once
from across_edge.versioning import deposit_version_identity
from conftest import make_deposit,make_fill

def evt(stage,trace='tr',deposit_id=1,output=990,**kw):
    d={'version':3,'stage':stage,'trace_id':trace,'deposit_key':f'42161:{deposit_id}','origin_chain_id':42161,'deposit_id':deposit_id,'destination_chain_id':8453,'candidate_type':'open','input_token':'0x1','output_token':'0x2','input_amount':1000,'output_amount':output,'exclusive_relayer':'0x0','exclusivity_deadline':0,'deposit_block':100,'max_block_number':100,'live_equivalent_confirmations_satisfied':True,'simulation_early_not_live_actionable':False};d.update(kw);return PREFIX+json.dumps(d)

def test_dotenv_boundary_rejects_secret_bearing_checkout(tmp_path):
    (tmp_path/'.env').write_text('API_TOKEN=not-a-real-token\n')
    try:audit_upstream_dotenv(tmp_path)
    except SafetyViolation as exc:assert '.env' in str(exc) and 'not-a-real-token' not in str(exc)
    else:raise AssertionError('dotenv reinjection was not blocked')
    (tmp_path/'.env').unlink();(tmp_path/'.env.example').write_text('API_TOKEN=example\n');(tmp_path/'.env.sample').write_text('API_TOKEN=sample\n');(tmp_path/'.env.template').write_text('API_TOKEN=template\n');assert audit_upstream_dotenv(tmp_path)['status']=='PASS'
    (tmp_path/'.env.local').write_text('API_TOKEN=real\n')
    try:audit_upstream_dotenv(tmp_path)
    except SafetyViolation:pass
    else:raise AssertionError('.env.local must remain blocked')

def test_dotenv_boundary_blocks_child_launch_before_process(monkeypatch,tmp_path):
    (tmp_path/'.git').mkdir();(tmp_path/'.env').write_text('API_TOKEN=sentinel-secret-value\n')
    monkeypatch.setattr('across_edge.upstream._git',lambda *_args:'741ca9f7d72923f7b13c1c2462ca90eba81e1a87' if _args[-1]=='HEAD' else 'across-protocol/relayer')
    launched=[]
    def fake_run(*args,**kwargs):launched.append((args,kwargs));return subprocess.CompletedProcess(args,0,'','')
    monkeypatch.setattr('across_edge.upstream.subprocess.run',fake_run)
    try:run_shadow_once(tmp_path)
    except SafetyViolation as exc:assert 'sentinel-secret-value' not in str(exc)
    else:raise AssertionError('unsafe child launch was not blocked')
    assert launched==[]

def test_attempts_are_immutable_and_not_mixed_across_loops(tmp_path):
    s=Store(tmp_path/'x');c=ShadowCoordinator(s,'r')
    c.ingest_line(evt('T0'),at_ns=10);c.ingest_line(evt('TA'),at_ns=20);c.ingest_line(evt('T1',profitability_decision='unprofitable'),at_ns=30)
    c.ingest_line(evt('T0'),at_ns=40);c.ingest_line(evt('TA'),at_ns=50);c.ingest_line(evt('T1',profitability_decision='profitable'),at_ns=60);c.ingest_line(evt('T2',simulation_result='success'),at_ns=70);c.ingest_line(evt('T3',transaction_ready=True),at_ns=80)
    rows=s.shadow_rows('r');assert len(rows)==2;old,new=rows;assert old['profitability_decision']=='unprofitable' and old['t2_monotonic_ns'] is None;assert new['profitability_decision']=='profitable' and new['t2_monotonic_ns']==70 and new['t3_monotonic_ns']==80;agg=s.aggregate('r','42161:1');assert agg['first_ready_attempt_id']==new['evaluation_attempt_id'] and agg['current_decision_attempt_id']==new['evaluation_attempt_id'];assert len(s.attempt_events('r',old['evaluation_attempt_id']))==3;s.close()

def test_speedup_version_changes_identity_without_guessing_unknown_update_fields(tmp_path):
    s=Store(tmp_path/'x');c=ShadowCoordinator(s,'r');c.ingest_line(evt('T0',output=990),at_ns=10);c.ingest_line(evt('TA'),at_ns=20);c.ingest_line(evt('T0',output=995),at_ns=30);rows=s.shadow_rows('r');assert len(rows)==2;assert rows[0]['deposit_key']==rows[1]['deposit_key'];assert rows[0]['deposit_version_id']!=rows[1]['deposit_version_id'];assert rows[0]['deposit_version_fingerprint']!=rows[1]['deposit_version_fingerprint'];assert rows[1]['deposit_version_provenance']=='PARTIAL_UNKNOWN_UPDATE_PROVENANCE';s.close()

def test_complete_speedup_identity_is_material_field_based():
    base={'origin_chain_id':42161,'destination_chain_id':8453,'deposit_id':7,'input_token':'0x1','output_token':'0x2','input_amount':1000,'output_amount':990,'recipient':'0xabc','message':'0x01','fill_deadline':999,'exclusive_relayer':'0x0','exclusivity_deadline':0,'updated_output_amount':990,'updated_recipient':'0xabc','updated_message':'0x01','speed_up_signature':'0xsig-a','update_authorization':'auth-a'}
    a=deposit_version_identity(base,'a');b=deposit_version_identity({**base,'updated_output_amount':980,'speed_up_signature':'0xsig-b'},'b');assert a[2]=='COMPLETE' and b[2]=='COMPLETE' and a[0]!=b[0] and a[1]!=b[1]

def test_cross_run_reorg_does_not_mutate_other_run(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);d=make_deposit(block=5);o.ingest_deposit(d,'A',destination_time=100,trace_id='A-t');o.ingest_fill(make_fill(block=20,tx='0xa'),'A',observed_monotonic_ns=200);o.ingest_deposit(d,'B',destination_time=100,trace_id='B-t');o.ingest_fill(make_fill(block=20,tx='0xa'),'B',observed_monotonic_ns=900);before=s.shadow_rows('A'),s.all_deposits('A'),s.all_fills('A'),s.canonical_counters('A');s.rewind_chain(8453,20,'B');after=s.shadow_rows('A'),s.all_deposits('A'),s.all_fills('A'),s.canonical_counters('A');assert before==after;assert s.all_fills('B')==[];s.close()

def test_cross_run_deposit_payloads_are_immutable(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);a=make_deposit(recipient='0x'+'a'*40,output_amount=990,block=5,tx='0xa');b=make_deposit(recipient='0x'+'b'*40,output_amount=970,block=6,tx='0xb');o.ingest_deposit(a,'A',destination_time=100,trace_id='A');o.ingest_deposit(b,'B',destination_time=100,trace_id='B');assert s.all_deposits('A')[0]['recipient']==a.recipient;assert s.all_deposits('B')[0]['recipient']==b.recipient;assert s.deposit(a.key)['recipient']==a.recipient;s.close()

def test_reorg_counter_state_matches_clean_canonical_ingest(tmp_path):
    wall='2026-08-10T00:00:00Z';dirty=Store(tmp_path/'dirty');o=Observer(dirty);d=make_deposit(block=5);o.ingest_deposit(d,'r',destination_time=100,trace_id='t');o.ingest_fill(make_fill(block=20,tx='0xorphan'),'r',observed_monotonic_ns=200,observed_wall_utc=wall);dirty.rewind_chain(8453,20,'r');o.ingest_fill(make_fill(block=20,tx='0xcanon'),'r',observed_monotonic_ns=300,observed_wall_utc=wall);clean=Store(tmp_path/'clean');o2=Observer(clean);o2.ingest_deposit(d,'r',destination_time=100,trace_id='t');o2.ingest_fill(make_fill(block=20,tx='0xcanon'),'r',observed_monotonic_ns=300,observed_wall_utc=wall);assert dirty.canonical_counters('r')==clean.canonical_counters('r');assert dirty.all_fills('r')==clean.all_fills('r');dirty.close();clean.close()

def test_replayed_fill_observation_is_run_local(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);f=make_fill(tx='0xsame',block=20,idx=1);o.ingest_fill(f,'A',observed_monotonic_ns=100);o.ingest_fill(f,'B',observed_monotonic_ns=900);assert s.all_fills('A')[0]['observed_monotonic_ns']==100;assert s.all_fills('B')[0]['observed_monotonic_ns']==900;s.close()

def test_report_is_run_pure_with_same_deposit_id(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);d=make_deposit();o.ingest_deposit(d,'A',destination_time=100,trace_id='A');o.ingest_fill(make_fill(tx='0xa',rel='0xaaa'),'A',observed_monotonic_ns=200);o.ingest_deposit(d,'B',destination_time=100,trace_id='B');o.ingest_fill(make_fill(tx='0xb',rel='0xbbb'),'B',observed_monotonic_ns=300);ra=build_report(s,'A');rb=build_report(s,'B');assert ra['competitors'][0]['relayer']=='0xaaa';assert rb['competitors'][0]['relayer']=='0xbbb';s.close()

def test_partial_economics_are_exposed_not_coerced_to_zero(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);d=make_deposit();r=o.ingest_deposit(d,'r',destination_time=100,trace_id='t');r.ta_monotonic_ns=1;r.economics={'gross_relayer_fee_usd_wei':'2000000000000000000','native_token_fill_cost_usd_wei':'500000000000000000','net_relayer_fee_usd_wei':'1500000000000000000','output_amount_usd_wei':'100000000000000000000'};s.upsert_shadow(r);rep=build_report(s,'r');assert rep['economics']['gross_relayer_fee_usd']['p50']=='2';assert rep['economics']['canonical_net_relayer_fee_usd']['p50']=='1.5';assert rep['economics']['rebalance_cost_usd']['evidence_class']=='UNKNOWN_REBALANCE_DEPENDENT';assert rep['economics']['final_post_rebalance_net_usd']['p50'] is None;s.close()

def test_economics_percentiles_require_two_samples_for_tail_values(tmp_path):
    s=Store(tmp_path/'x');o=Observer(s);d=make_deposit();r=o.ingest_deposit(d,'r',destination_time=100,trace_id='t');r.economics={'gross_relayer_fee_usd_wei':'2000000000000000000'};s.upsert_shadow(r);rep=build_report(s,'r');e=rep['economics']['gross_relayer_fee_usd'];assert e['count']==1 and e['p50']=='2' and e['p10'] is None and e['p90'] is None and e['sample_status']=='SAMPLE_INSUFFICIENT';s.close()
