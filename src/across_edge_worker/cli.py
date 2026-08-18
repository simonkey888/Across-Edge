from __future__ import annotations
import argparse,json
from pathlib import Path
from .worker import run_job
def main(argv=None):
 p=argparse.ArgumentParser(prog="across-edge-worker");p.add_argument("command",nargs="?",default="run",choices=["run","cancel"]);p.add_argument("--job",type=Path);p.add_argument("--state-dir",type=Path,required=True);p.add_argument("--output-dir",type=Path);a=p.parse_args(argv)
 if a.command=="cancel":
  a.state_dir.mkdir(parents=True,exist_ok=True);marker=a.state_dir/"cancel.requested";marker.write_text("cancel_requested\n");print(json.dumps({"status":"CANCEL_REQUESTED","state_dir":str(a.state_dir)},sort_keys=True));return 0
 if a.job is None or a.output_dir is None:p.error("run requires --job and --output-dir")
 try:r=run_job(a.job,a.state_dir,a.output_dir)
 except Exception as exc:print(json.dumps({"status":"FAILED_CLOSED","error_class":type(exc).__name__,"error":str(exc)},sort_keys=True));return 2
 print(json.dumps(r,sort_keys=True));return 0 if r.get("status") in {"RESULT_READY","CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY"} else 2
if __name__=="__main__":raise SystemExit(main())
