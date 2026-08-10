import json,pytest
from across_edge.coordinator import ShadowCoordinator,PREFIX,UpstreamEventError
from across_edge.storage import Store
def evt(stage,**kw):
 d={'version':2,'stage':stage,'trace_id':'tr','deposit_key':'42161:1','origin_chain_id':42161,'deposit_id':1,'destination_chain_id':8453,'candidate_type':'open','wall_utc':'2026-08-10T00:00:00Z'};d.update(kw);return PREFIX+json.dumps(d)
def test_canonical_event_sequence(tmp_path):
 s=Store(tmp_path/'x.db');c=ShadowCoordinator(s,'r');c.ingest_line(evt('T0'),at_ns=10);c.ingest_line(evt('T1',eligible=True,profitability_decision='profitable',economics={'net_relayer_fee_usd_wei':'1'}),at_ns=20);c.ingest_line(evt('T2',simulation_result='success'),at_ns=30);c.ingest_line(evt('T3',transaction_ready=True,transaction_serialized='0xabc'),at_ns=40);r=s.shadow_rows('r')[0];assert r['transaction_ready'] and r['economics']['net_relayer_fee_usd_wei']=='1';s.close()
def test_non_t0_first_rejected(tmp_path):
 s=Store(tmp_path/'x.db');c=ShadowCoordinator(s,'r')
 with pytest.raises(UpstreamEventError):c.ingest_line(evt('T1'),at_ns=10)
 s.close()
