#!/usr/bin/env python3
from __future__ import annotations
import argparse,fcntl,json,os,shutil,signal,socket,subprocess,sys,threading,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
import re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from across_edge.chain_observer import ChainSpec,RpcObserver
from across_edge.coordinator import ShadowCoordinator
from across_edge.reporting import export_artifacts
from across_edge.rpc import JsonRpcClient,fallback_read
from across_edge.runmeta import RunMetadata,git_head
from across_edge.safety import validate_shadow_environment
from across_edge.storage import Store
from across_edge.supervisor import ContinuousSupervisor
from across_edge.upstream import PINNED_SHA,safe_upstream_command,verify_patch,verify_upstream_checkout

DEFAULT_MAINNET_RPC_A='https://eth.drpc.org'
DEFAULT_MAINNET_RPC_B='https://gateway.tenderly.co/public/mainnet'
DEFAULT_ARBITRUM_RPC_A='https://arb1.arbitrum.io/rpc'
DEFAULT_ARBITRUM_RPC_B='https://arbitrum.drpc.org'
DEFAULT_BASE_RPC_A='https://mainnet.base.org'
DEFAULT_BASE_RPC_B='https://base.drpc.org'

def utc_now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def atomic_json(path:Path,payload:dict):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');tmp.replace(path)
def public_rpc_override(name,default):
    value=os.environ.get(name,default).strip();p=urlsplit(value)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.query or p.fragment:raise RuntimeError(f'{name} must be a public credential-free HTTPS endpoint')
    return value

def rpc_profile():
    return {
      'mainnet_a':public_rpc_override('ACROSS_EDGE_RPC_MAINNET_PRIMARY',DEFAULT_MAINNET_RPC_A),
      'mainnet_b':public_rpc_override('ACROSS_EDGE_RPC_MAINNET_FALLBACK',DEFAULT_MAINNET_RPC_B),
      'arbitrum_a':public_rpc_override('ACROSS_EDGE_RPC_ARBITRUM_PRIMARY',DEFAULT_ARBITRUM_RPC_A),
      'arbitrum_b':public_rpc_override('ACROSS_EDGE_RPC_ARBITRUM_FALLBACK',DEFAULT_ARBITRUM_RPC_B),
      'base_a':public_rpc_override('ACROSS_EDGE_RPC_BASE_PRIMARY',DEFAULT_BASE_RPC_A),
      'base_b':public_rpc_override('ACROSS_EDGE_RPC_BASE_FALLBACK',DEFAULT_BASE_RPC_B),
    }

def patch_is_applied(repo:Path,patch:Path)->bool:
    return subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(patch)],capture_output=True,text=True,check=False).returncode==0

def _redis_ping(timeout=1.0):
    try:
        with socket.create_connection(('127.0.0.1',6379),timeout=timeout) as sock:
            sock.sendall(b'*1\r\n$4\r\nPING\r\n');return sock.recv(64).startswith(b'+PONG')
    except OSError:return False

def ensure_local_redis():
    if _redis_ping():return None
    binary=shutil.which('redis-server') or str(ROOT/'.bin'/'redis-server')
    if not Path(binary).exists():raise RuntimeError('redis-server is required locally for the pinned Across relayer shadow runtime')
    proc=subprocess.Popen([binary,'--bind','127.0.0.1','--port','6379','--protected-mode','yes','--save','','--appendonly','no','--maxmemory','256mb','--maxmemory-policy','allkeys-lru'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    for _ in range(50):
        if proc.poll() is not None:raise RuntimeError('local redis-server exited during startup')
        if _redis_ping():return proc
        time.sleep(.1)
    proc.terminate();raise RuntimeError('local redis-server did not become ready')

def runtime_env(polling_delay:int):
    if polling_delay<=0:raise ValueError('continuous runtime requires POLLING_DELAY > 0')
    rpc=rpc_profile();keep={k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','LC_ALL','TMPDIR','TERM'} and v}
    keep['NODE_OPTIONS']='--max-old-space-size=768'
    keep.update({
      'NODE_MAX_CONCURRENCY':'1','NODE_RETRIES':'1','NODE_TIMEOUT_1':'5000','NODE_TIMEOUT_42161':'8000','NODE_TIMEOUT_8453':'8000',
      'MAX_BLOCK_LOOK_BACK':'{"1":250000}','POLLING_DELAY':str(polling_delay),
      'SEND_RELAYS':'false','SEND_TRANSACTIONS':'false','SEND_SLOW_RELAYS':'false','RELAYER_USE_INVENTORY_MANAGER':'false',
      'EXECUTOR_ENABLED':'false','PROPOSER_ENABLED':'false','DISPUTER_ENABLED':'false','REBALANCER_ENABLED':'false','SWAP_REBALANCER_ENABLED':'false',
      'NOMINATION_WRITES_ENABLED':'false','REGISTRATION_WRITES_ENABLED':'false','RELAYER_ORIGIN_CHAINS':'[42161]','RELAYER_DESTINATION_CHAINS':'[8453]',
      'RPC_PROVIDERS_1':'M1,M2','RPC_PROVIDERS_42161':'A1,A2','RPC_PROVIDERS_8453':'B1,B2',
      'RPC_PROVIDER_M1_1':rpc['mainnet_a'],'RPC_PROVIDER_M2_1':rpc['mainnet_b'],
      'RPC_PROVIDER_A1_42161':rpc['arbitrum_a'],'RPC_PROVIDER_A2_42161':rpc['arbitrum_b'],
      'RPC_PROVIDER_B1_8453':rpc['base_a'],'RPC_PROVIDER_B2_8453':rpc['base_b'],
      'ACROSS_EDGE_INSTRUMENTATION':'true','ACROSS_EDGE_ZERO_WRITE_SHADOW':'true','REDIS_URL':'redis://127.0.0.1:6379',
      'ADDRESS_FILTER_PATH':'./across-edge-addresses.json',
    });validate_shadow_environment(keep,['--wallet','void']);return keep

class FallbackRpc:
    def __init__(self,*urls):self.clients=[JsonRpcClient(u,timeout=8) for u in urls]
    def call(self,method,params=None):return fallback_read(self.clients,method,params)

def acquire_lock(lock_path:Path,pid_path:Path):
    lock_path.parent.mkdir(parents=True,exist_ok=True);fd=open(lock_path,'a+')
    try:fcntl.flock(fd.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise RuntimeError('another Across-Edge shadow supervisor is already active')
    pid_path.write_text(str(os.getpid())+'\n');return fd

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('relayer_dir');p.add_argument('--db',default='evidence/ORDER010_FINAL/shadow.sqlite');p.add_argument('--run-id',default='order010-live');p.add_argument('--out',default='evidence/ORDER010_FINAL/live');p.add_argument('--duration',type=float,default=0);p.add_argument('--polling-delay',type=int,default=5);p.add_argument('--observer-interval',type=float,default=2);p.add_argument('--export-interval',type=float,default=30);p.add_argument('--source-head',default='');a=p.parse_args(argv)
    repo=Path(a.relayer_dir).resolve();manifest=json.loads((ROOT/'config/upstream-pin.json').read_text());patch=ROOT/manifest['instrumentation_patch'];verify_upstream_checkout(repo);verify_patch(patch,manifest['instrumentation_patch_sha256'])
    if not patch_is_applied(repo,patch):print('INSTRUMENTATION_PATCH_NOT_APPLIED',file=sys.stderr);return 3
    source_head=a.source_head or git_head(ROOT)
    if not source_head or source_head=='UNKNOWN':raise RuntimeError('final source head must be supplied for source-bound runtime provenance')
    local_address_file=repo/'across-edge-addresses.json';created_address_file=False
    if not local_address_file.exists():local_address_file.write_text('[]\n');created_address_file=True
    redis_proc=ensure_local_redis();env=runtime_env(a.polling_delay);rpc=rpc_profile();db=Path(a.db) if Path(a.db).is_absolute() else ROOT/a.db;out_path=Path(a.out) if Path(a.out).is_absolute() else ROOT/a.out;root_ev=ROOT/'evidence'/'ORDER010_FINAL';heartbeat_path=root_ev/'heartbeat.json';pid_path=root_ev/'shadow.pid';lock_path=root_ev/'shadow.lock';lock_fd=acquire_lock(lock_path,pid_path)
    store=Store(db);meta=RunMetadata(a.run_id,our_sha=source_head,upstream_sha=PINNED_SHA,config=env,routes=['42161->8453'],endpoints=list(rpc.values()));meta.payload['patch_sha256']=manifest['instrumentation_patch_sha256'];store.set_run_metadata(a.run_id,meta.payload);base_coord=ShadowCoordinator(store,a.run_id)
    activation_log=root_ev/'activation.log';runtime_markers={'relayer_init_complete':False,'relayer_loops_completed':0,'real_unfilled_deposits':0}
    class LoggingCoordinator:
        def ingest_line(self,line):
            with activation_log.open('a') as fh:fh.write(line+'\n')
            if 'Completed one-time init.' in line:runtime_markers['relayer_init_complete']=True
            m=re.search(r'(\d+) unfilled deposits found\.',line)
            if m:runtime_markers['relayer_loops_completed']+=1;runtime_markers['real_unfilled_deposits']+=int(m.group(1))
            return base_coord.ingest_line(line)
    coord=LoggingCoordinator()
    specs=[(ChainSpec(42161,'Arbitrum One',rpc['arbitrum_a'],'0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A'),rpc['arbitrum_a'],rpc['arbitrum_b']),(ChainSpec(8453,'Base',rpc['base_a'],'0x09aea4b2242abC8bb4BB78D537A67a245A7bEC64'),rpc['base_a'],rpc['base_b'])]
    def make_factory(spec,u1,u2):
        def factory():return RpcObserver(Store(db),a.run_id,spec,backfill_blocks=128,rpc=FallbackRpc(u1,u2))
        return factory
    observers=[make_factory(*item) for item in specs];stop=threading.Event()
    def sig(*_):stop.set()
    old={x:signal.signal(x,sig) for x in (signal.SIGTERM,signal.SIGINT)}
    def spawn():return subprocess.Popen(safe_upstream_command(repo),cwd=repo,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1,start_new_session=True)
    started_utc=meta.payload['start_utc'];started_monotonic=time.monotonic()
    def periodic():
        report=export_artifacts(store,a.run_id,out_path);health=sup.health();components=health['components'];rel=components['relayer'];o0=components.get('observer:0',{});o1=components.get('observer:1',{});errors=[x for x in [rel.get('last_error'),o0.get('last_error'),o1.get('last_error')] if x]
        heartbeat={'run_id':a.run_id,'source_head':source_head,'upstream_sha':PINNED_SHA,'patch_sha256':manifest['instrumentation_patch_sha256'],'started_at_utc':started_utc,'last_heartbeat_utc':utc_now(),'qualification_runtime_seconds':int(time.monotonic()-started_monotonic),'supervisor_pid':os.getpid(),'relayer_alive':bool(rel.get('alive')),'observer_arbitrum_alive':bool(o0.get('alive')),'observer_base_alive':bool(o1.get('alive')),'observer_cycles':int(o0.get('cycles',0))+int(o1.get('cycles',0)),'relayer_restarts':int(rel.get('restarts',0)),'last_relayer_exit':rel.get('last_exit_code'),'last_error':' | '.join(errors),'send_relays':False,'send_transactions':False,'wallet':'void','spend_usd':0,'private_keys':0,'signing':0,'transactions':0,'write_rpc':0,'onchain_value_transfer':0,'deposits_observed':report.get('deposits_observed',0),'fills_observed':sum((report.get('fill_type_counts') or {}).values()),'decode_gaps':int(report.get('unresolved_decode_count') or 0),'relayer_init_complete':runtime_markers['relayer_init_complete'],'relayer_loops_completed':runtime_markers['relayer_loops_completed'],'real_unfilled_deposits':runtime_markers['real_unfilled_deposits']};atomic_json(heartbeat_path,heartbeat);atomic_json(out_path/'health.json',health)
    sup=ContinuousSupervisor(coordinator=coord,observers=observers,process_factory=spawn,observer_interval_s=a.observer_interval,restart_delay_s=2,max_relayer_restarts=1000000,periodic=periodic,periodic_interval_s=min(60,a.export_interval))
    try:
        result=sup.run(stop,max_runtime_s=None if a.duration<=0 else a.duration)
    finally:
        try:periodic()
        except Exception:pass
        for x,h in old.items():signal.signal(x,h)
        store.close();pid_path.unlink(missing_ok=True);fcntl.flock(lock_fd.fileno(),fcntl.LOCK_UN);lock_fd.close()
        if redis_proc is not None and redis_proc.poll() is None:
            try:os.killpg(os.getpgid(redis_proc.pid),signal.SIGTERM)
            except Exception:redis_proc.terminate()
        if created_address_file:local_address_file.unlink(missing_ok=True)
    return 0 if not result.errors else 2
if __name__=='__main__':raise SystemExit(main())
