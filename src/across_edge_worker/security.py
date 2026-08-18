from __future__ import annotations
import hashlib,os,re,signal,subprocess,tempfile,time
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
SENSITIVE_NAME=re.compile(r"(SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE[_-]?KEY|MNEMONIC|SEED|AWS_|AZURE_|GCP_|GOOGLE_APPLICATION_CREDENTIALS|CLOUDFLARE|STRIPE|PAYPAL|KMS|WALLET)",re.I)
SECRET_PATTERNS=(re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),re.compile(r"\b(?:sk|rk|pk)_(?:live|prod)_[A-Za-z0-9_-]{12,}\b"),re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),re.compile(r"(?i)(?:private[_ -]?key|mnemonic|seed phrase)\s*[=:]\s*[^\s]{8,}"))
SAFE_ENV_NAMES={"PATH","LANG","LC_ALL","TZ","PYTHONPATH","SYSTEMROOT","WINDIR","TMP","TEMP"}
def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as handle:
  for chunk in iter(lambda:handle.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def scrub_environment(source:dict[str,str]|None=None,*,home:str|None=None)->dict[str,str]:
 source=dict(os.environ if source is None else source);clean={}
 for key,value in source.items():
  if key in SAFE_ENV_NAMES and not SENSITIVE_NAME.search(key):clean[key]=value
 clean["HOME"]=home or tempfile.mkdtemp(prefix="across-edge-worker-home-");clean["GIT_CONFIG_NOSYSTEM"]="1";clean["GIT_TERMINAL_PROMPT"]="0";clean["GIT_OPTIONAL_LOCKS"]="0";return clean
def assert_no_sensitive_environment(env:dict[str,str])->None:
 leaked=sorted(key for key in env if SENSITIVE_NAME.search(key))
 if leaked:raise ValueError("sensitive_environment_exposed:"+",".join(leaked))
def validate_relative_path(root:Path,relative:str,allowed_paths:Iterable[str],*,must_exist:bool=False)->Path:
 if not relative or Path(relative).is_absolute():raise ValueError("path_escape:absolute_or_empty")
 rel=Path(relative)
 if any(part in {"..",""} for part in rel.parts):raise ValueError("path_escape:traversal")
 allowed=[Path(item) for item in allowed_paths]
 if not any(rel==item or item in rel.parents for item in allowed):raise ValueError("path_outside_allowed_scope")
 root_resolved=root.resolve();candidate=root/rel
 if must_exist and not candidate.exists():raise ValueError("path_missing")
 current=root
 for part in rel.parts:
  current=current/part
  if current.is_symlink():raise ValueError("path_escape:symlink")
 resolved=candidate.resolve(strict=False)
 if resolved!=root_resolved and root_resolved not in resolved.parents:raise ValueError("path_escape:resolved_outside_root")
 return candidate
def scan_text_for_secrets(text:str)->list[str]:return [f"secret_pattern_{i}" for i,p in enumerate(SECRET_PATTERNS) if p.search(text)]
def scan_tree_for_secrets(root:Path)->list[str]:
 findings=[]
 for path in sorted(root.rglob("*")):
  if not path.is_file() or ".git" in path.parts:continue
  try:text=path.read_text(errors="strict")
  except (UnicodeDecodeError,OSError):continue
  findings.extend(f"{path.relative_to(root)}:{item}" for item in scan_text_for_secrets(text))
 return findings
def endpoint_host(url:str)->str:
 parsed=urlparse(url)
 if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:raise ValueError("endpoint_policy_invalid_url")
 if parsed.query:raise ValueError("endpoint_policy_query_forbidden")
 if parsed.fragment:raise ValueError("endpoint_policy_fragment_forbidden")
 return parsed.hostname.lower()
def assert_endpoint_allowed(url:str,allowed_urls:Iterable[str])->None:
 allowed={item.rstrip("/") for item in allowed_urls};normalized=url.rstrip("/");endpoint_host(url)
 for item in allowed:endpoint_host(item)
 if normalized not in allowed:raise ValueError("endpoint_not_allowlisted")
def validate_target_repository(value:str)->None:
 parsed=urlparse(value)
 if parsed.scheme:
  if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError("target_repository_remote_policy_forbidden")
  return
 if value.startswith("git@") or "://" in value:raise ValueError("target_repository_remote_policy_forbidden")
 path=Path(value).expanduser()
 if not path.exists():raise ValueError("target_repository_local_missing")
def _terminate_group(process:subprocess.Popen[str])->None:
 if process.poll() is not None:return
 try:os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=3)
 except (ProcessLookupError,subprocess.TimeoutExpired):
  try:os.killpg(process.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  process.wait()
def run_bounded_process(command:list[str],*,cwd:Path,timeout:float,env:dict[str,str]|None=None,cancel_marker:Path|None=None)->subprocess.CompletedProcess[str]:
 if timeout<=0:raise TimeoutError("bounded_process_timeout")
 safe_env=scrub_environment(env);assert_no_sensitive_environment(safe_env);process=subprocess.Popen(command,cwd=cwd,env=safe_env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True);deadline=time.monotonic()+timeout
 while process.poll() is None:
  if cancel_marker is not None and cancel_marker.exists():_terminate_group(process);raise InterruptedError("worker_cancelled")
  if time.monotonic()>=deadline:_terminate_group(process);raise TimeoutError("bounded_process_timeout")
  time.sleep(.05)
 stdout,stderr=process.communicate();return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
def prepare_isolated_target(target_repository:str,target_base_sha:str,workdir:Path,*,timeout:float=120,cancel_marker:Path|None=None)->Path:
 if len(target_base_sha)!=40:raise ValueError("target_base_sha_invalid")
 validate_target_repository(target_repository);target=workdir/"target"
 if target.exists():
  observed=subprocess.check_output(["git","-C",str(target),"rev-parse","HEAD"],text=True).strip()
  if observed!=target_base_sha:raise ValueError("recovered_target_sha_mismatch")
  return target
 workdir.mkdir(parents=True,exist_ok=True);env=scrub_environment();assert_no_sensitive_environment(env);deadline=time.monotonic()+timeout
 def run(args:list[str])->None:
  remaining=deadline-time.monotonic();result=run_bounded_process(args,cwd=workdir,timeout=remaining,env=env,cancel_marker=cancel_marker)
  if result.returncode!=0:raise RuntimeError("git_target_prepare_failed:"+result.stderr.strip()[:500])
 run(["git","-c","core.hooksPath=/dev/null","clone","--quiet","--no-checkout","--filter=blob:none","--",target_repository,str(target)])
 run(["git","-C",str(target),"-c","core.hooksPath=/dev/null","checkout","--detach",target_base_sha])
 run(["git","-C",str(target),"config","core.hooksPath","/dev/null"])
 observed=subprocess.check_output(["git","-C",str(target),"rev-parse","HEAD"],text=True).strip()
 if observed!=target_base_sha:raise ValueError("target_sha_mismatch")
 return target
def snapshot_tree_hash(root:Path)->str:
 material=[]
 for path in sorted(root.rglob("*")):
  if path.is_file() and ".git" not in path.parts:material.append(f"{path.relative_to(root)}:{sha256_file(path)}")
 return hashlib.sha256("\n".join(material).encode()).hexdigest()
