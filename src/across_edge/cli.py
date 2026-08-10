from __future__ import annotations

import argparse
import json
import os

from .reporting import export_artifacts
from .safety import validate_shadow_environment
from .storage import Store

BANNER = "ACROSS-EDGE ORDER-001 — SHADOW ONLY — LIVE FINANCIAL EXECUTION PROHIBITED"

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=BANNER)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("safety-check")
    report = sub.add_parser("report"); report.add_argument("db"); report.add_argument("run_id"); report.add_argument("out")
    args = p.parse_args(argv)
    print(BANNER)
    validate_shadow_environment(os.environ, ["--wallet", "void"])
    if args.cmd == "safety-check":
        print("SAFETY=PASS")
        return 0
    store = Store(args.db)
    try:
        result = export_artifacts(store, args.run_id, args.out)
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        store.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
