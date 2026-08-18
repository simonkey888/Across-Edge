#!/usr/bin/env python3
from __future__ import annotations
import argparse,fcntl,json,os,signal,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def utc():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def atomic(path,payload):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');tmp.replace(path)
def kill_group(proc,grace=10):
 if proc.poll() is not None:return
 try:os.killpg(proc.pid,signal.SIGTERM)
 except ProcessLookupError:return
 deadline=time.monotonic()+grace
 while time.monotonic()<deadline:
  if proc.poll() is not None:return
  time.sleep(.1)
 try:os.killpg(proc.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 try:proc.wait(timeout=2)
 except Exception:pass
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('relayer_dir');p.add_argument('--source-head',required=True);p.add_argument('--run-id',default='order010-live');p.add_argument('--state-dir',default='evidence/ORDER010_FINAL');p.add_argument('--polling-delay',type=int,default=5);a=p.parse_args(argv)
 state=Path(a.state_dir) if Path(a.state_dir).is_absolute() else ROOT/a.state_dir;state.mkdir(parents=True,exist_ok=True);lock=(state/'watchdog.lock').open('a+');
 try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:print('WATCHDOG_ALREADY_RUNNING',file=sys.stderr);return 2
 (state/'watchdog.pid').write_text(str(os.getpid())+'\n');stop=False;child=None;restarts=0
 def sig(*_):
  nonlocal stop;stop=True
 def sleep_or_stop(seconds):
  deadline=time.monotonic()+seconds
  while not stop and time.monotonic()<deadline:time.sleep(min(.2,max(0,deadline-time.monotonic())))
 old={s:signal.signal(s,sig) for s in (signal.SIGTERM,signal.SIGINT)}
 try:
  while not stop:
   log=state/'activation.log'
   if log.exists() and log.stat().st_size>20_000_000:
    oldlog=state/'activation.log.1';oldlog.unlink(missing_ok=True);log.replace(oldlog)
   stream=log.open('a',buffering=1)
   cmd=[sys.executable,str(ROOT/'scripts'/'shadow_run.py'),str(Path(a.relayer_dir).resolve()),'--source-head',a.source_head,'--run-id',a.run_id,'--db',str(state/'shadow.sqlite'),'--out',str(state/'live'),'--polling-delay',str(a.polling_delay),'--export-interval','30']
   child=subprocess.Popen(cmd,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,text=True,start_new_session=True);started=utc();atomic(state/'watchdog.json',{'watchdog_pid':os.getpid(),'child_pid':child.pid,'child_started_at_utc':started,'last_watchdog_heartbeat_utc':utc(),'watchdog_restarts':restarts,'running':True})
   while not stop and child.poll() is None:
    atomic(state/'watchdog.json',{'watchdog_pid':os.getpid(),'child_pid':child.pid,'child_started_at_utc':started,'last_watchdog_heartbeat_utc':utc(),'watchdog_restarts':restarts,'running':True});sleep_or_stop(10)
   rc=child.poll();stream.close()
   if stop:kill_group(child);break
   kill_group(child,2);restarts+=1;atomic(state/'watchdog.json',{'watchdog_pid':os.getpid(),'child_pid':None,'last_child_exit':rc,'last_watchdog_heartbeat_utc':utc(),'watchdog_restarts':restarts,'running':True});sleep_or_stop(min(30,2**min(restarts,5)))
 finally:
  if child is not None:kill_group(child)
  atomic(state/'watchdog.json',{'watchdog_pid':os.getpid(),'child_pid':None,'last_watchdog_heartbeat_utc':utc(),'watchdog_restarts':restarts,'running':False});(state/'watchdog.pid').unlink(missing_ok=True)
  for s,h in old.items():signal.signal(s,h)
 return 0
if __name__=='__main__':raise SystemExit(main())
