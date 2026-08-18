from __future__ import annotations
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' / 'ATM-WORKER-READY-R1'
REQUIRED = {'REMOTE_TRUTH.md', 'WORKER_CONTRACT.json', 'CAPABILITY_MATRIX.json', 'SECURITY_BOUNDARY.md', 'CHAIN_RPC_BOUNDARY.md', 'NEGATIVE_TESTS.json', 'CRASH_RECOVERY.json', 'REAL_WORLD_SHADOW.json', 'PROJECT_PRESERVATION.md', 'TEST_RESULTS.txt', 'CI_EXACT_HEAD.md', 'INTEGRATION_NOTES.md'}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    missing = sorted((name for name in REQUIRED if not (EVIDENCE / name).is_file()))
    if missing:
        raise SystemExit('MISSING_EVIDENCE=' + ','.join(missing))
    for name in ('WORKER_CONTRACT.json', 'CAPABILITY_MATRIX.json', 'NEGATIVE_TESTS.json', 'CRASH_RECOVERY.json', 'REAL_WORLD_SHADOW.json'):
        json.loads((EVIDENCE / name).read_text())
    manifest_path = EVIDENCE / 'MANIFEST.sha256'
    if not manifest_path.is_file():
        raise SystemExit('MISSING_MANIFEST')
    entries: dict[str, str] = {}
    for line in manifest_path.read_text().splitlines():
        if not line.strip():
            continue
        sha, rel = line.split('  ', 1)
        if rel in entries:
            raise SystemExit('DUPLICATE_MANIFEST_ENTRY=' + rel)
        entries[rel] = sha
    expected = {name: digest(EVIDENCE / name) for name in REQUIRED}
    if set(entries) != set(expected):
        raise SystemExit('MANIFEST_FILE_SET_MISMATCH')
    bad = sorted((name for name, sha in expected.items() if entries[name] != sha))
    if bad:
        raise SystemExit('MANIFEST_DIGEST_MISMATCH=' + ','.join(bad))
    print(f'ATM_WORKER_EVIDENCE_MANIFEST=PASS files={len(expected)}')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
