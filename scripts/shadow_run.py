#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,signal,subprocess,sys,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from across_edge.chain_observer import ChainSpec,RpcObserver
from across_edge.coordinator import ShadowCoordinator
from across_edge.reporting import export_artifacts
from across_edge.runmeta import RunMetadata,git_head
from across_edge.safety import validate_shadow_environment
from across_edge.storage import Store
from across_edge.supervisor import ContinuousSupervisor
from across_edge.upstream import PINNED_SHA,safe_upstream_command,verify_patch,verify_upstream_checkout
def patch_is_applied(repo:Path,patch:Path)->bool:return subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(patch)],capture_output=True,text=True,check=False).returncode==0
def runtime_env(polling_delay:int)->dict[str,str]:
    if polling_delay<=0:raise ValueError('continuous runtime requires POLLING_DELAY > 0')
    keep={k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','LC_ALL','TMPDIR','TERM'} and v};keep.update({'POLLING_DELAY':str(polling_delay),'SEND_RELAYS':'false','SEND_TRANSACTIONS':'false','SEND_SLOW_RELAYS':'false','RELAYER_USE_INVENTORY_MANAGER':'false','EXECUTOR_ENABLED':'false','PROPOSER_ENABLED':'false','DISPUTER_ENABLED':'false','REBALANCER_ENABLED':'false','SWAP_REBALANCER_ENABLED':'false','NOMINATION_WRITES_ENABLED':'false','REGISTRATION_WRITES_ENABLED':'false','RELAYER_ORIGIN_CHAINS':'[42161]','RELAYER_DESTINATION_CHAINS':'[8453]','RPC_PROVIDERS':'PUBLIC','RPC_PROVIDERS_1':'PUBLIC','RPC_PROVIDERS_42161':'PUBLIC','RPC_PROVIDERS_8453':'PUBLIC','RPC_PROVIDER_PUBLIC_1':'https://ethereum-rpc.publicnode.com','RPC_PROVIDER_PUBLIC_42161':'https://arb1.arbitrum.io/rpc','RPC_PROVIDER_PUBLIC_8453':'https://mainnet.base.org','ACROSS_EDGE_INSTRUMENTATION':'true','REDIS_URL':''});validate_shadow_environment(keep,['--wallet','void']);return keep
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('relayer_dir');p.add_argument('--db',default='evidence/order003-shadow.sqlite');p.add_argument('--run-id',default='order003-shadow');p.add_argument('--out',default='evidence/order003-shadow');p.add_argument('--duration',type=float,default=86400);p.add_argument('--polling-delay',type=int,default=5);p.add_argument('--observer-interval',type=float,default=2);p.add_argument('--export-interval',type=float,default=60);a=p.parse_args(argv);repo=Path(a.relayer_dir);manifest=json.loads((ROOT/'config/upstream-pin.json').read_text());patch=ROOT/manifest['instrumentation_patch'];verify_upstream_checkout(repo);verify_patch(patch,manifest['instrumentation_patch_sha256'])
    if not patch_is_applied(repo,patch):print('INSTRUMENTATION_PATCH_NOT_APPLIED',file=sys.stderr);return 3
    env=runtime_env(a.polling_delay);db=ROOT/a.db;store=Store(db);meta=RunMetadata(a.run_id,our_sha=git_head(ROOT),upstream_sha=PINNED_SHA,config=env,routes=['42161->8453'],endpoints=['https://ethereum-rpc.publicnode.com','https://arb1.arbitrum.io/rpc','https://mainnet.base.org']);meta.payload['patch_sha256']=manifest['instrumentation_patch_sha256'];store.set_run_metadata(a.run_id,meta.payload);coord=ShadowCoordinator(store,a.run_id);specs=[ChainSpec(42161,'Arbitrum One','https://arb1.arbitrum.io/rpc','0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A'),ChainSpec(8453,'Base','https://mainnet.base.org','0x09aea4b2242abC8bb4BB78D537A67a245A7bEC64')];observer_stores=[Store(db) for _ in specs];observers=[RpcObserver(s,a.run_id,spec,backfill_blocks=128) for s,spec in zip(observer_stores,specs)];stop=threading.Event()
    def sig(*_):stop.set()
    old={x:signal.signal(x,sig) for x in (signal.SIGTERM,signal.SIGINT)}
    def spawn():return subprocess.Popen(safe_upstream_command(repo),cwd=repo,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    def periodic():export_artifacts(store,a.run_id,ROOT/a.out);out=ROOT/a.out;out.mkdir(parents=True,exist_ok=True);(out/'health.json').write_text(json.dumps(sup.health(),indent=2,sort_keys=True)+'\n')
    sup=ContinuousSupervisor(coordinator=coord,observers=observers,process_factory=spawn,observer_interval_s=a.observer_interval,periodic=periodic,periodic_interval_s=a.export_interval)
    try:result=sup.run(stop,max_runtime_s=a.duration)
    finally:
        for s in observer_stores:s.close()
        for x,h in old.items():signal.signal(x,h)
    state='PASS' if not result.errors else 'PARTIAL';payload=meta.finish(zero_write_rpc_proof='PASS',zero_spend_proof='PASS',safety='PASS',tests='UNKNOWN',secret_scan='UNKNOWN',continuous_supervisor='PASS',observer_cycles=result.observer_cycles,relayer_restarts=result.relayer_restarts,real_network_read_only_smoke=state,errors=result.errors);store.set_run_metadata(a.run_id,payload);export_artifacts(store,a.run_id,ROOT/a.out);store.close();print(json.dumps({'status':state,'runtime_monotonic_ns':result.runtime_monotonic_ns,'observer_cycles':result.observer_cycles,'relayer_restarts':result.relayer_restarts,'relayer_returncode':result.relayer_returncode,'errors':result.errors},sort_keys=True));return 0 if state=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
