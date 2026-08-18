from __future__ import annotations
import argparse,json
from pathlib import Path
from .worker import run_job
def main():
    p=argparse.ArgumentParser(prog="across-edge-worker");p.add_argument("run",nargs="?");p.add_argument("--job",type=Path,required=True);p.add_argument("--state-dir",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);a=p.parse_args()
    try:r=run_job(a.job,a.state_dir,a.output_dir)
    except Exception as exc:print(json.dumps({"status":"FAILED_CLOSED","error_class":type(exc).__name__,"error":str(exc)},sort_keys=True));return 2
    print(json.dumps(r,sort_keys=True));return 0 if r.get("status") in {"RESULT_READY","CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY"} else 2
if __name__=="__main__":raise SystemExit(main())
