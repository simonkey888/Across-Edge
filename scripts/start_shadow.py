#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('relayer_dir');p.add_argument('--source-head',required=True);p.add_argument('--run-id',default='order010-live');p.add_argument('--polling-delay',type=int,default=5);a=p.parse_args()
 if len(a.source_head)!=40 or any(c not in '0123456789abcdef' for c in a.source_head.lower()):raise SystemExit('source head must be exact 40-char SHA')
 state=ROOT/'evidence'/'ORDER010_FINAL';state.mkdir(parents=True,exist_ok=True);cfg={'enabled':True,'relayer_dir':str(Path(a.relayer_dir).resolve()),'source_head':a.source_head,'run_id':a.run_id,'polling_delay':a.polling_delay};(state/'service-config.json').write_text(json.dumps(cfg,indent=2,sort_keys=True)+'\n')
 rc=subprocess.call([sys.executable,str(ROOT/'scripts'/'ensure_shadow.py')],cwd=ROOT)
 if rc:return rc
 for _ in range(60):
  if (state/'watchdog.pid').exists():print('SHADOW_WATCHDOG_STARTED pid='+ (state/'watchdog.pid').read_text().strip());return 0
  time.sleep(.1)
 raise SystemExit('watchdog failed to start')
if __name__=='__main__':raise SystemExit(main())
