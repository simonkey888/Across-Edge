#!/usr/bin/env python3
import os,signal,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];pid_path=ROOT/'evidence'/'ORDER010_FINAL'/'shadow.pid'
if not pid_path.exists():print('SHADOW_ALREADY_STOPPED');raise SystemExit(0)
pid=int(pid_path.read_text().strip());os.kill(pid,signal.SIGTERM)
for _ in range(200):
    try:os.kill(pid,0)
    except ProcessLookupError:print('SHADOW_STOPPED_CLEANLY');raise SystemExit(0)
    time.sleep(.1)
print('SHADOW_STOP_TIMEOUT',file=__import__('sys').stderr);raise SystemExit(2)
