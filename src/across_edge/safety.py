from __future__ import annotations
import os,re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping,Sequence
from urllib.parse import urlsplit,urlunsplit
PROHIBITED_SECRET_KEYS={'PRIVATE_KEY','MNEMONIC','SECRET','ARWEAVE_WALLET_JWK','DISPATCHER_KEYS','GCKMS_CONFIG','GOOGLE_APPLICATION_CREDENTIALS'}
PROHIBITED_TRUE_FLAGS={'SEND_RELAYS','SEND_TRANSACTIONS','SEND_SLOW_RELAYS','RELAYER_USE_INVENTORY_MANAGER','EXECUTOR_ENABLED','PROPOSER_ENABLED','DISPUTER_ENABLED','SWAP_REBALANCER_ENABLED','REBALANCER_ENABLED','NOMINATION_WRITES_ENABLED','REGISTRATION_WRITES_ENABLED'}
LIVE_RPC_METHODS={'eth_sendRawTransaction','eth_sendTransaction','wallet_sendTransaction','eth_signTransaction','personal_sendTransaction'}
READ_ONLY_RPC_METHODS={'eth_blockNumber','eth_getBlockByNumber','eth_getBlockByHash','eth_getLogs','eth_getTransactionByHash','eth_getTransactionReceipt','eth_getTransactionCount','eth_call','eth_estimateGas','eth_chainId','net_version','web3_clientVersion','eth_gasPrice','eth_feeHistory'}
_SECRET_RE=re.compile(r'(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+\-/=]{8,}|(gh[pousr]_[A-Za-z0-9_]{20,})|(0x[0-9a-f]{64})|((?:mnemonic|private[_ -]?key|seed phrase|api[_ -]?key|token|password)\s*[=:]\s*)[^\s,;]+')
class SafetyViolation(RuntimeError):pass
@dataclass(frozen=True)
class SafetyState:send_relays:bool;send_transactions:bool;wallet_type:str;secrets_present:tuple[str,...]
def _truthy(v):return str(v or '').strip().lower() in {'1','true','yes','on'}
def sanitize_endpoint(url:str)->str:
 try:
  p=urlsplit(url);host=p.hostname or '';port=f':{p.port}' if p.port else '';return urlunsplit((p.scheme,host+port,p.path,'',''))
 except Exception:return '<redacted-endpoint>'
def sanitize_text(value:object)->str:
 text=str(value);text=re.sub(r'https?://[^\s]+',lambda m:sanitize_endpoint(m.group(0)),text);return _SECRET_RE.sub(lambda m:(m.group(1) or m.group(4) or '')+'<REDACTED>',text)
def validate_shadow_environment(env:Mapping[str,str]|None=None,argv:Sequence[str]=())->SafetyState:
 env=dict(os.environ if env is None else env);secrets=tuple(sorted(k for k in PROHIBITED_SECRET_KEYS if env.get(k)))
 if secrets:raise SafetyViolation('ORDER-004 forbids real secret material: '+', '.join(secrets))
 enabled=tuple(sorted(k for k in PROHIBITED_TRUE_FLAGS if _truthy(env.get(k))))
 if enabled:raise SafetyViolation('LIVE_EXECUTION_PROHIBITED: '+', '.join(enabled))
 args=list(argv);wallet='void'
 if '--wallet' in args:
  i=args.index('--wallet')
  if i+1>=len(args):raise SafetyViolation('--wallet requires a value')
  wallet=args[i+1]
 if wallet!='void':raise SafetyViolation('ORDER-004 requires upstream --wallet void')
 return SafetyState(False,False,wallet,secrets)
def assert_read_only_rpc_method(method:str)->None:
 if method in LIVE_RPC_METHODS or method.startswith('eth_send') or method.startswith('personal_') or method.startswith('wallet_'):raise SafetyViolation(f'LIVE_EXECUTION_PROHIBITED: RPC method {method}')
 if method not in READ_ONLY_RPC_METHODS:raise SafetyViolation(f'RPC method is not allow-listed: {method}')
def audit_upstream_dotenv(relayer_dir:str|Path)->dict:
 root=Path(relayer_dir);blocked=[]
 for p in root.rglob('.env*'):
  if not p.is_file() or any(part in {'.git','node_modules'} for part in p.parts):continue
  if p.name=='.env.example':continue
  blocked.append(str(p.relative_to(root)))
 if blocked:raise SafetyViolation('loadable dotenv/config source present; launch blocked: '+','.join(sorted(blocked)))
 return {'status':'PASS','loadable_dotenv_files':[]}
class ProhibitedBroadcaster:
 def broadcast(self,*_args,**_kwargs):raise SafetyViolation('LIVE_EXECUTION_PROHIBITED')
