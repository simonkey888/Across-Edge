#!/usr/bin/env python3
from __future__ import annotations
import json,os,signal,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'evidence'/'ORDER010_FINAL'

def alive(pid:int)->bool:
    try:os.kill(pid,0);return True
    except (ProcessLookupError,PermissionError):return False

def main():
    cfg=STATE/'service-config.json'
    if cfg.exists():
        try:
            d=json.loads(cfg.read_text());d['enabled']=False;cfg.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
        except Exception:pass
    pidfile=STATE/'watchdog.pid'
    if not pidfile.exists():print('SHADOW_ALREADY_STOPPED');return 0
    try:pid=int(pidfile.read_text().strip())
    except ValueError:pidfile.unlink(missing_ok=True);print('SHADOW_ALREADY_STOPPED');return 0
    if not alive(pid):pidfile.unlink(missing_ok=True);print('SHADOW_ALREADY_STOPPED');return 0
    try:os.killpg(pid,signal.SIGTERM)
    except (ProcessLookupError,PermissionError):
        try:os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:pass
    deadline=time.monotonic()+15
    while alive(pid) and time.monotonic()<deadline:time.sleep(.1)
    if alive(pid):
        try:os.killpg(pid,signal.SIGKILL)
        except (ProcessLookupError,PermissionError):
            try:os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:pass
        deadline=time.monotonic()+3
        while alive(pid) and time.monotonic()<deadline:time.sleep(.1)
    if alive(pid):print('SHADOW_STOP_TIMEOUT',file=__import__('sys').stderr);return 2
    pidfile.unlink(missing_ok=True);print('SHADOW_STOPPED_CLEANLY');return 0
if __name__=='__main__':raise SystemExit(main())
