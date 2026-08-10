#!/usr/bin/env python3
from __future__ import annotations
import re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATTERNS=[('private_key',re.compile(r'(?i)(private[_ -]?key|mnemonic|seed phrase)\s*[=:]\s*[\'\"]?(?:0x)?[0-9a-f]{64}')),('github_token',re.compile(r'gh[pousr]_[A-Za-z0-9_]{20,}')),('bearer',re.compile(r'(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._~+\-/=]{8,}')),('url_credentials',re.compile(r'https?://[^\s/@:]+:[^\s/@]+@')),('api_key_assignment',re.compile(r'(?i)(?:api[_-]?key|access[_-]?token|password)\s*[=:]\s*[\'\"]?[A-Za-z0-9._~+\-/=]{20,}'))]
ALLOW_EXACT={'tests/fixtures/secret_scanner_placeholders.txt'}
def tracked_files():
 p=subprocess.run(['git','-C',str(ROOT),'ls-files','-z'],capture_output=True,check=False)
 if p.returncode==0 and p.stdout:return [ROOT/x.decode() for x in p.stdout.split(b'\0') if x]
 return [p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and '.pytest_cache' not in p.parts]
findings=[]
for path in tracked_files():
 rel=str(path.relative_to(ROOT)).replace('\\','/')
 if rel in ALLOW_EXACT or path.suffix.lower() in {'.png','.jpg','.jpeg','.zip','.sqlite','.db','.pyc'}:continue
 try:text=path.read_text(errors='ignore')
 except OSError:continue
 for name,pattern in PATTERNS:
  for m in pattern.finditer(text):findings.append((rel,name,text.count('\n',0,m.start())+1))
if findings:
 for rel,name,line in findings:print(f'SECRET_SCAN_FINDING path={rel} type={name} line={line}')
 sys.exit(1)
print('SECRET_SCAN_FULL_COMMITTED_SURFACE=PASS')
