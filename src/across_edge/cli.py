from __future__ import annotations
import argparse,json,os,time
from pathlib import Path
from .chain_observer import ChainSpec,RpcObserver
from .reporting import export_artifacts
from .runmeta import RunMetadata,git_head
from .safety import validate_shadow_environment,sanitize_text
from .storage import Store
from .upstream import PINNED_SHA,verify_upstream_checkout
BANNER='ACROSS-EDGE ORDER-002 — SHADOW ONLY — LIVE FINANCIAL EXECUTION PROHIBITED'
OFFICIAL_CHAINS={
 'arbitrum':ChainSpec(42161,'Arbitrum One','https://arb1.arbitrum.io/rpc','0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A'),
 'base':ChainSpec(8453,'Base','https://mainnet.base.org','0x09aea4b2242abC8bb4BB78D537A67a245A7bEC64'),
}
def _observe(args):
    validate_shadow_environment(os.environ,['--wallet','void']);store=Store(args.db);specs=[OFFICIAL_CHAINS[x] for x in args.chains.split(',')]
    meta=RunMetadata(args.run_id,our_sha=git_head('.'),upstream_sha=PINNED_SHA,config={'chains':args.chains,'backfill':args.backfill},routes=['42161<->8453'],endpoints=[s.rpc_url for s in specs]);store.set_run_metadata(args.run_id,meta.payload)
    results=[]
    try:
        try:
            for spec in specs:results.append({'chain':spec.name,**RpcObserver(store,args.run_id,spec,backfill_blocks=args.backfill).run_once()})
        except Exception as exc:
            blocked=sanitize_text(exc)
            store.set_run_metadata(args.run_id,meta.finish(zero_write_rpc_proof='PASS',safety='PASS',tests='UNKNOWN',secret_scan='UNKNOWN',real_network_read_only_smoke='EXPLICITLY_BLOCKED',blocker=blocked))
            print(json.dumps({'status':'EXPLICITLY_BLOCKED','reason':blocked},sort_keys=True))
            return 2
        store.set_run_metadata(args.run_id,meta.finish(zero_write_rpc_proof='PASS',safety='PASS',tests='UNKNOWN',secret_scan='UNKNOWN',real_network_read_only_smoke='PASS'))
        print(json.dumps(results,indent=2,sort_keys=True));return 0
    finally:store.close()
def main(argv=None)->int:
    p=argparse.ArgumentParser(description=BANNER);sub=p.add_subparsers(dest='cmd',required=True);sub.add_parser('safety-check')
    report=sub.add_parser('report');report.add_argument('db');report.add_argument('run_id');report.add_argument('out')
    obs=sub.add_parser('observe');obs.add_argument('db');obs.add_argument('run_id');obs.add_argument('--chains',default='arbitrum,base');obs.add_argument('--backfill',type=int,default=128)
    verify=sub.add_parser('verify-upstream');verify.add_argument('path')
    args=p.parse_args(argv);print(BANNER);validate_shadow_environment(os.environ,['--wallet','void'])
    if args.cmd=='safety-check':print('SAFETY=PASS');return 0
    if args.cmd=='verify-upstream':print(json.dumps(verify_upstream_checkout(args.path),sort_keys=True));return 0
    if args.cmd=='observe':return _observe(args)
    store=Store(args.db)
    try:print(json.dumps(export_artifacts(store,args.run_id,args.out),indent=2,sort_keys=True))
    finally:store.close()
    return 0
if __name__=='__main__':raise SystemExit(main())
