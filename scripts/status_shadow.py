#!/usr/bin/env python3
import json,os,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=ROOT/'evidence'/'ORDER010_FINAL'/'heartbeat.json'
if not p.exists():print(json.dumps({'active':False,'reason':'heartbeat_missing'}));raise SystemExit(2)
h=json.loads(p.read_text());last=datetime.fromisoformat(h['last_heartbeat_utc'].replace('Z','+00:00'));age=max(0,(datetime.now(timezone.utc)-last).total_seconds());pid=int(h.get('supervisor_pid') or 0)
try:os.kill(pid,0);process=True
except Exception:process=False
h['heartbeat_age_seconds']=round(age,3);h['process_currently_running']=process;h['active']=process and age<=120 and h.get('relayer_alive') and h.get('observer_arbitrum_alive') and h.get('observer_base_alive');print(json.dumps(h,sort_keys=True));raise SystemExit(0 if h['active'] else 2)
