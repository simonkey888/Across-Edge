#!/usr/bin/env python3
from __future__ import annotations
import fcntl,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def alive(pid):
 try:os.kill(int(pid),0);return True
 except (OSError,ValueError,TypeError):return False
def main():
 state=ROOT/'evidence'/'ORDER010_FINAL';state.mkdir(parents=True,exist_ok=True);lock=(state/'ensure.lock').open('a+')
 try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:return 0
 cfg_path=state/'service-config.json'
 if not cfg_path.exists():return 0
 cfg=json.loads(cfg_path.read_text())
 if not cfg.get('enabled'):return 0
 pidfile=state/'watchdog.pid'
 if pidfile.exists() and alive(pidfile.read_text().strip()):return 0
 log=(state/'ensure.log').open('a',buffering=1)
 subprocess.Popen([sys.executable,str(ROOT/'scripts'/'shadow_watchdog.py'),cfg['relayer_dir'],'--source-head',cfg['source_head'],'--run-id',cfg.get('run_id','order010-live'),'--state-dir',str(state),'--polling-delay',str(cfg.get('polling_delay',5))],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
 return 0
if __name__=='__main__':raise SystemExit(main())
