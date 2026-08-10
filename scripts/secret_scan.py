#!/usr/bin/env python3
from __future__ import annotations
import re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SKIP={".git",".pytest_cache","__pycache__","evidence"}
PATTERNS=[("ethereum_private_key",re.compile(r"(?i)(private[_ -]?key|mnemonic|seed phrase)\s*[=:]\s*['\"]?0x?[0-9a-f]{64}")),("github_token",re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}")),("generic_bearer",re.compile(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9._~-]{20,}"))]
findings=[]
for path in ROOT.rglob("*"):
    if not path.is_file() or any(part in SKIP for part in path.parts):continue
    if path.suffix.lower() in {".png",".jpg",".jpeg",".zip",".sqlite",".db"}:continue
    try:text=path.read_text(errors="ignore")
    except OSError:continue
    for name,pattern in PATTERNS:
        for m in pattern.finditer(text):findings.append((str(path.relative_to(ROOT)),name,m.start()))
if findings:
    for f in findings:print("SECRET_SCAN_FINDING",*f)
    sys.exit(1)
print("SECRET_SCAN=PASS")
