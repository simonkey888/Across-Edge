from __future__ import annotations
import hashlib,os,re,subprocess
from pathlib import Path
from typing import Mapping
from .safety import audit_upstream_dotenv,validate_shadow_environment,sanitize_text
PINNED_SHA='741ca9f7d72923f7b13c1c2462ca90eba81e1a87';CANONICAL_REPO='across-protocol/relayer'
def _git(path,*args):
    p=subprocess.run(['git','-C',str(path),*args],text=True,capture_output=True,check=False)
    if p.returncode:raise RuntimeError(sanitize_text(p.stderr or p.stdout or 'git failed'))
    return p.stdout.strip()
def normalize_remote(value:str)->str:
    v=value.strip().removesuffix('.git');m=re.search(r'(?:github\.com[/:])([^/]+/[^/]+)$',v);return m.group(1).lower() if m else v.lower()
def verify_upstream_checkout(relayer_dir:str|Path)->dict:
    relayer_dir=Path(relayer_dir)
    if not (relayer_dir/'.git').exists():raise RuntimeError('upstream checkout is not a git repository')
    head=_git(relayer_dir,'rev-parse','HEAD');remote=_git(relayer_dir,'remote','get-url','origin')
    if normalize_remote(remote)!=CANONICAL_REPO:raise RuntimeError('unexpected upstream repository identity')
    if head!=PINNED_SHA:raise RuntimeError(f'upstream HEAD mismatch: expected {PINNED_SHA}, got {head}')
    dotenv=audit_upstream_dotenv(relayer_dir);return {'repository':CANONICAL_REPO,'head':head,'dotenv':dotenv}
def sha256_file(path:str|Path)->str:
    h=hashlib.sha256();h.update(Path(path).read_bytes());return h.hexdigest()
def verify_patch(path:str|Path,expected_sha256:str)->None:
    actual=sha256_file(path)
    if actual!=expected_sha256:raise RuntimeError(f'instrumentation patch hash mismatch: {actual}')
def safe_upstream_command(relayer_dir:str|Path,address:str='0x0000000000000000000000000000000000000000')->list[str]:return ['node','./dist/index.js','--relayer','--wallet','void','--address',address]
def safe_env(base:Mapping[str,str]|None=None)->dict[str,str]:
    env=dict(base or {})
    for key in list(env):
        ku=key.upper()
        if key in {'PRIVATE_KEY','MNEMONIC','SECRET','DISPATCHER_KEYS','ARWEAVE_WALLET_JWK','GCKMS_CONFIG','GOOGLE_APPLICATION_CREDENTIALS'} or any(x in ku for x in ('MNEMONIC','PRIVATE_KEY','SEED_PHRASE','BINANCE','HYPERLIQUID')):env.pop(key,None)
    for k in ('SEND_RELAYS','SEND_TRANSACTIONS','SEND_SLOW_RELAYS','RELAYER_USE_INVENTORY_MANAGER','EXECUTOR_ENABLED','PROPOSER_ENABLED','DISPUTER_ENABLED','SWAP_REBALANCER_ENABLED','REBALANCER_ENABLED','NOMINATION_WRITES_ENABLED','REGISTRATION_WRITES_ENABLED'):env[k]='false'
    env['ACROSS_EDGE_INSTRUMENTATION']='true';env['ACROSS_EDGE_ZERO_WRITE_SHADOW']='true';validate_shadow_environment(env,['--wallet','void']);return env
def run_shadow_once(relayer_dir:str|Path,extra_env:Mapping[str,str]|None=None)->subprocess.CompletedProcess[str]:
    verify_upstream_checkout(relayer_dir);env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','USER','LOGNAME','TMPDIR','TEMP','TMP','TERM','LANG','LC_ALL','NODE_OPTIONS'}};env.update(extra_env or {});env=safe_env(env);cmd=safe_upstream_command(relayer_dir);validate_shadow_environment(env,cmd);return subprocess.run(cmd,cwd=relayer_dir,env=env,text=True,capture_output=True,check=False)
