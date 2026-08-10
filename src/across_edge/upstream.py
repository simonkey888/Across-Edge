from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping

from .safety import validate_shadow_environment

PINNED_SHA = "741ca9f7d72923f7b13c1c2462ca90eba81e1a87"

def safe_upstream_command(relayer_dir: str | Path, address: str = "0x0000000000000000000000000000000000000000") -> list[str]:
    return ["yarn", "relay", "--wallet", "void", "--address", address]


def safe_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base or {})
    env["SEND_RELAYS"] = "false"
    env["SEND_TRANSACTIONS"] = "false"
    env["SEND_SLOW_RELAYS"] = "false"
    for key in ("PRIVATE_KEY", "MNEMONIC", "SECRET", "DISPATCHER_KEYS", "ARWEAVE_WALLET_JWK"):
        env.pop(key, None)
    validate_shadow_environment(env, ["--wallet", "void"])
    return env


def run_shadow_once(relayer_dir: str | Path, extra_env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    relayer_dir = Path(relayer_dir)
    env = os.environ.copy()
    env.update(safe_env(extra_env))
    cmd = safe_upstream_command(relayer_dir)
    validate_shadow_environment(env, cmd)
    return subprocess.run(cmd, cwd=relayer_dir, env=env, text=True, capture_output=True, check=False)
