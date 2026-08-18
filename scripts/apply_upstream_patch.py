#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from across_edge.upstream import verify_upstream_checkout,verify_patch
from across_edge.safety import sanitize_text

def run(repo,*args):return subprocess.run(['git','-C',str(repo),*args],text=True,capture_output=True,check=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('relayer_dir');p.add_argument('--check-only',action='store_true');a=p.parse_args();repo=Path(a.relayer_dir);m=json.loads((ROOT/'config/upstream-pin.json').read_text());patch=ROOT/m['instrumentation_patch'];verify_upstream_checkout(repo);verify_patch(patch,m['instrumentation_patch_sha256'])
 check=run(repo,'apply','--check',str(patch))
 if check.returncode!=0:
  rev=run(repo,'apply','--reverse','--check',str(patch))
  if rev.returncode==0:print('UPSTREAM_PATCH=ALREADY_APPLIED');return 0
  print('UPSTREAM_PATCH_CHECK=FAIL '+sanitize_text(check.stderr),file=sys.stderr);return 2
 if a.check_only:print('UPSTREAM_PATCH_CHECK=PASS');return 0
 applied=run(repo,'apply',str(patch))
 if applied.returncode:print('UPSTREAM_PATCH_APPLY=FAIL '+sanitize_text(applied.stderr),file=sys.stderr);return 3
 print('UPSTREAM_PATCH_APPLY=PASS');return 0
if __name__=='__main__':raise SystemExit(main())
