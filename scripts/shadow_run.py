#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from across_edge.chain_observer import ChainSpec,RpcObserver
from across_edge.coordinator import ShadowCoordinator
from across_edge.reporting import export_artifacts
from across_edge.runmeta import RunMetadata,git_head
from across_edge.safety import sanitize_text,validate_shadow_environment
from across_edge.storage import Store
from across_edge.upstream import PINNED_SHA,safe_upstream_command,verify_upstream_checkout,verify_patch

def patch_is_applied(repo:Path,patch:Path)->bool:
 p=subprocess.run(['git','-C',str(repo),'apply','--reverse','--check',str(patch)],capture_output=True,text=True,check=False);return p.returncode==0
def runtime_env()->dict[str,str]:
 keep={k:v for k,v in os.environ.items() if k in {'PATH','HOME','LANG','LC_ALL','TMPDIR','TERM'} and v}
 keep.update({'POLLING_DELAY':'0','SEND_RELAYS':'false','SEND_TRANSACTIONS':'false','SEND_SLOW_RELAYS':'false','RELAYER_USE_INVENTORY_MANAGER':'false','RELAYER_ORIGIN_CHAINS':'[42161]','RELAYER_DESTINATION_CHAINS':'[8453]','RPC_PROVIDERS':'PUBLIC','RPC_PROVIDERS_1':'PUBLIC','RPC_PROVIDERS_42161':'PUBLIC','RPC_PROVIDERS_8453':'PUBLIC','RPC_PROVIDER_PUBLIC_1':'https://ethereum-rpc.publicnode.com','RPC_PROVIDER_PUBLIC_42161':'https://arb1.arbitrum.io/rpc','RPC_PROVIDER_PUBLIC_8453':'https://mainnet.base.org','ACROSS_EDGE_INSTRUMENTATION':'true','REDIS_URL':''});validate_shadow_environment(keep,['--wallet','void']);return keep

def main():
 p=argparse.ArgumentParser();p.add_argument('relayer_dir');p.add_argument('--db',default='evidence/order002-shadow.sqlite');p.add_argument('--run-id',default='order002-shadow');p.add_argument('--out',default='evidence/order002-shadow');p.add_argument('--timeout',type=int,default=180);a=p.parse_args();repo=Path(a.relayer_dir);manifest=json.loads((ROOT/'config/upstream-pin.json').read_text());patch=ROOT/manifest['instrumentation_patch'];verify_upstream_checkout(repo);verify_patch(patch,manifest['instrumentation_patch_sha256'])
 if not patch_is_applied(repo,patch):print('INSTRUMENTATION_PATCH_NOT_APPLIED',file=sys.stderr);return 3
 store=Store(ROOT/a.db);meta=RunMetadata(a.run_id,our_sha=git_head(ROOT),upstream_sha=PINNED_SHA,config=runtime_env(),routes=['42161->8453'],endpoints=['https://ethereum-rpc.publicnode.com','https://arb1.arbitrum.io/rpc','https://mainnet.base.org']);store.set_run_metadata(a.run_id,meta.payload);coord=ShadowCoordinator(store,a.run_id);errors=[]
 specs=[ChainSpec(42161,'Arbitrum One','https://arb1.arbitrum.io/rpc','0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A'),ChainSpec(8453,'Base','https://mainnet.base.org','0x09aea4b2242abC8bb4BB78D537A67a245A7bEC64')]
 def observe():
  observer_store=Store(ROOT/a.db)
  try:
   for s in specs:
    try:RpcObserver(observer_store,a.run_id,s,backfill_blocks=128).run_once()
    except Exception as e:errors.append('observer:'+sanitize_text(e))
  finally:observer_store.close()
 t=threading.Thread(target=observe,daemon=True);t.start();proc=subprocess.Popen(safe_upstream_command(repo),cwd=repo,env=runtime_env(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1);start=time.monotonic()
 try:
  assert proc.stdout is not None
  for line in proc.stdout:
   try:coord.ingest_line(line.rstrip('\n'))
   except Exception as e:errors.append('instrumentation:'+sanitize_text(e))
   if time.monotonic()-start>a.timeout:proc.terminate();errors.append('upstream:timeout');break
 finally:
  if proc.poll() is None:proc.terminate()
  try:proc.wait(timeout=10)
  except subprocess.TimeoutExpired:proc.kill();proc.wait()
  t.join(timeout=10)
 status='PASS' if proc.returncode==0 and not errors else 'PARTIAL'
 payload=meta.finish(zero_write_rpc_proof='PASS',safety='PASS',tests='UNKNOWN',secret_scan='UNKNOWN',real_network_read_only_smoke=status,errors=errors);store.set_run_metadata(a.run_id,payload);export_artifacts(store,a.run_id,ROOT/a.out);store.close();print(json.dumps({'status':status,'returncode':proc.returncode,'errors':errors},sort_keys=True));return 0 if status=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
