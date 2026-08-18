#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADOW_RUN = ROOT / "scripts" / "shadow_run.py"
LOOKBACK_SECONDS = 3600
RESTART_BUDGET = 3
HEAP_LIMIT_MB = 2048

spec = importlib.util.spec_from_file_location("across_edge_order011_base_shadow", SHADOW_RUN)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load base shadow runner")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

_original_runtime_env = base.runtime_env
_original_supervisor = base.ContinuousSupervisor


def runtime_env(polling_delay: int):
    env = _original_runtime_env(polling_delay)
    # Diagnostic stopgap explicitly allowed by ORDER-011: give V8 enough headroom to complete
    # bootstrap so loop-end telemetry can prove whether memory stabilizes. This is not a
    # profitability/economic change and is not accepted as the final fix if memory grows unbounded.
    env["MAX_RELAYER_DEPOSIT_LOOK_BACK"] = str(LOOKBACK_SECONDS)
    env["NODE_OPTIONS"] = f"--max-old-space-size={HEAP_LIMIT_MB}"
    env["ACROSS_EDGE_ORDER011"] = "true"
    return env


class BoundedRestartSupervisor(_original_supervisor):
    def __init__(self, *args, **kwargs):
        # The base ORDER010 runner historically passed a very large restart allowance.
        # ORDER011 is fail-closed: persistent child failure must terminate instead of cycling indefinitely.
        kwargs["max_relayer_restarts"] = RESTART_BUDGET
        super().__init__(*args, **kwargs)


base.runtime_env = runtime_env
base.ContinuousSupervisor = BoundedRestartSupervisor


def main(argv=None) -> int:
    os.environ["ACROSS_EDGE_ORDER011_LOOKBACK_SECONDS"] = str(LOOKBACK_SECONDS)
    os.environ["ACROSS_EDGE_ORDER011_RESTART_BUDGET"] = str(RESTART_BUDGET)
    os.environ["ACROSS_EDGE_ORDER011_HEAP_DIAGNOSTIC_MB"] = str(HEAP_LIMIT_MB)
    return int(base.main(argv) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
