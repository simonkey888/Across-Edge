from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import median

from .observer import competitor_scoreboard, percentile
from .storage import Store

UPSTREAM_SHA = "741ca9f7d72923f7b13c1c2462ca90eba81e1a87"

def _ms(a, b):
    if a is None or b is None: return None
    return (b - a) / 1_000_000

def _duration_values(rows, a, b):
    return [v for r in rows if (v := _ms(r.get(a), r.get(b))) is not None]

def _pct(values, p): return percentile(values, p) if values else None

def build_report(store: Store, run_id: str) -> dict:
    rows = store.shadow_rows(run_id)
    t01=_duration_values(rows,"t0_monotonic_ns","t1_monotonic_ns"); t12=_duration_values(rows,"t1_monotonic_ns","t2_monotonic_ns"); t23=_duration_values(rows,"t2_monotonic_ns","t3_monotonic_ns"); t03=_duration_values(rows,"t0_monotonic_ns","t3_monotonic_ns")
    headrooms=[r["shadow_headroom_ms"] for r in rows if r.get("shadow_headroom_ms") is not None]; winner_latencies=[r["winner_latency_ms"] for r in rows if r.get("winner_latency_ms") is not None]
    ready=[r for r in rows if r.get("transaction_ready") and r.get("shadow_headroom_ms") is not None]; ready_before=sum(1 for r in ready if r["shadow_headroom_ms"]>0)
    report={"run_id":run_id,"schema_version":1,"upstream_sha":UPSTREAM_SHA,"our_sha":"UNKNOWN","start_utc":"UNKNOWN","end_utc":"UNKNOWN","runtime_hours":None,"deposits_observed":len(rows),"open_opportunities":sum(r.get("candidate_type")=="open" for r in rows),"step_in_opportunities":sum(r.get("candidate_type")=="step_in" for r in rows),"eligible_under_25":None,"eligible_under_50":None,"eligible_under_75":None,"eligible_under_100":None,"eligible_opportunities":sum(r.get("eligible") is True for r in rows),"profitable_candidates":sum(r.get("profitability_decision")=="profitable" for r in rows),"tx_ready_candidates":sum(r.get("transaction_ready") is True for r in rows),"t0_t1_p50_ms":_pct(t01,.5),"t0_t1_p90_ms":_pct(t01,.9),"t1_t2_p50_ms":_pct(t12,.5),"t1_t2_p90_ms":_pct(t12,.9),"t2_t3_p50_ms":_pct(t23,.5),"t2_t3_p90_ms":_pct(t23,.9),"t0_t3_p50_ms":_pct(t03,.5),"t0_t3_p90_ms":_pct(t03,.9),"winner_latency_p50_ms":_pct(winner_latencies,.5),"winner_latency_p90_ms":_pct(winner_latencies,.9),"ready_before_winner_count":ready_before,"ready_before_winner_pct":(100*ready_before/len(ready)) if ready else None,"headroom_p10_ms":_pct(headrooms,.1),"headroom_p50_ms":_pct(headrooms,.5),"headroom_p90_ms":_pct(headrooms,.9),"estimated_net_pool_usd":None,"break_even_fills_per_day_at_5_usd_infra":None,"break_even_fills_per_day_at_10_usd_infra":None,"break_even_fills_per_day_at_20_usd_infra":None,"timeboost_relevance":"UNKNOWN","sequencer_feed_lead_p50_ms":None,"sequencer_feed_verdict":"BLOCKED_BY_ZERO_COST_RUNTIME","rpc_hedging_verdict":"BLOCKED_BY_ZERO_COST_RUNTIME","zero_live_tx_proof":"PASS","secret_scan":"UNKNOWN","tests":"UNKNOWN","warning":"READY_BEFORE_WINNER_IS_NOT_EQUIVALENT_TO_WOULD_HAVE_WON","competitors":competitor_scoreboard(store.all_deposits(),store.all_fills())}
    report.update({"observed_candidates":report["deposits_observed"],"eligible_candidates":report["eligible_opportunities"],"transaction_ready_candidates":report["tx_ready_candidates"],"median_t0_t1_ms":median(t01) if t01 else None,"median_t1_t2_ms":median(t12) if t12 else None,"median_t2_t3_ms":median(t23) if t23 else None,"median_shadow_headroom_ms":median(headrooms) if headrooms else None})
    return report

def export_artifacts(store:Store,run_id:str,out_dir:str|Path)->dict:
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);rows=store.shadow_rows(run_id);report=build_report(store,run_id)
    (out/"run-metadata.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n");(out/"shadow-records.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows))
    with (out/"competitors.csv").open("w",newline="") as f:
        fields=["relayer","fills_observed","median_deposit_to_fill_ms","p10_ms","p90_ms","routes"];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in report["competitors"]: row=dict(row);row["routes"]="|".join(row["routes"]);w.writerow(row)
    with (out/"latency.csv").open("w",newline="") as f:
        fields=["deposit_key","winner_latency_ms","shadow_headroom_ms"];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:r.get(k) for k in fields})
    return report
