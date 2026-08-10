from __future__ import annotations
import time
from dataclasses import dataclass
from .evm import FUNDS_DEPOSITED_TOPIC0,FILLED_RELAY_TOPIC0,decode_funds_deposited,decode_filled_relay
from .observer import Observer
from .rpc import JsonRpcClient
from .storage import Store
@dataclass(frozen=True)
class ChainSpec:chain_id:int;name:str;rpc_url:str;spoke_pool:str;deployment_block:int=0
class RpcObserver:
    def __init__(self,store:Store,run_id:str,spec:ChainSpec,relayer_address:str|None=None,backfill_blocks:int=256,reorg_depth:int=32,*,rpc=None,decode_deposit=decode_funds_deposited,decode_fill=decode_filled_relay):self.store=store;self.run_id=run_id;self.spec=spec;self.rpc=rpc or JsonRpcClient(spec.rpc_url);self.observer=Observer(store,relayer_address);self.backfill_blocks=backfill_blocks;self.reorg_depth=reorg_depth;self.decode_deposit=decode_deposit;self.decode_fill=decode_fill
    def _block(self,n):return self.rpc.call('eth_getBlockByNumber',[hex(n),False]).result
    @staticmethod
    def _event_id(log):idx=log.get('logIndex',-1);idx=int(idx,16) if isinstance(idx,str) else int(idx);return f"{str(log.get('transactionHash','')).lower()}:{idx}"
    def run_once(self)->dict:
        head=int(self.rpc.call('eth_blockNumber').result,16);cursor=self.store.get_cursor('spokepool',self.spec.chain_id,self.run_id);reorg=False
        if cursor and cursor['last_block_number'] is not None:
            prior=self._block(cursor['last_block_number'])
            if prior and cursor['last_block_hash'] and prior.get('hash','').lower()!=cursor['last_block_hash'].lower():
                rewind=max(self.spec.deployment_block,cursor['last_block_number']-self.reorg_depth+1);self.store.rewind_chain(self.spec.chain_id,rewind,self.run_id);cursor=None;reorg=True;self.store.bump_counter(self.run_id,'reorgs_detected');start=rewind
            else:start=cursor['next_block']
        else:start=max(self.spec.deployment_block,head-self.backfill_blocks+1)
        if start>head:return {'head':head,'from_block':start,'to_block':head,'logs':0,'accepted':0,'errors':0,'reorg':reorg,'cursor_next_block':start}
        logs=self.rpc.call('eth_getLogs',[{'address':self.spec.spoke_pool,'fromBlock':hex(start),'toBlock':hex(head),'topics':[[FUNDS_DEPOSITED_TOPIC0,FILLED_RELAY_TOPIC0]]}]).result or [];block_cache={};accepted=0;errors=0;error_blocks=[]
        for log in sorted(logs,key=lambda x:(int(x['blockNumber'],16),int(x.get('logIndex','0x0'),16))):
            received_ns=time.perf_counter_ns();bn=int(log['blockNumber'],16)
            if bn not in block_cache:block_cache[bn]=self._block(bn)
            ts=int(block_cache[bn]['timestamp'],16);topic=(log.get('topics') or [''])[0].lower();eid=self._event_id(log)
            try:
                if topic==FUNDS_DEPOSITED_TOPIC0.lower():self.observer.ingest_deposit(self.decode_deposit(log,origin_chain_id=self.spec.chain_id,block_timestamp=ts),self.run_id,source_block_number=bn,source_block_hash=block_cache[bn].get('hash',''));accepted+=1
                elif topic==FILLED_RELAY_TOPIC0.lower():self.observer.ingest_fill(self.decode_fill(log,destination_chain_id=self.spec.chain_id,block_timestamp=ts),self.run_id,observed_monotonic_ns=received_ns);accepted+=1
                self.store.resolve_decode_gap(self.run_id,self.spec.chain_id,eid)
            except Exception as exc:errors+=1;error_blocks.append(bn);self.store.bump_counter(self.run_id,'decode_errors');self.store.record_decode_gap(self.run_id,self.spec.chain_id,log,exc)
        head_block=block_cache.get(head) or self._block(head);head_hash=head_block.get('hash','') if head_block else '';head_ts=int(head_block['timestamp'],16) if head_block else 0;self.observer.refresh_candidate_states(self.run_id,self.spec.chain_id,head_ts,source_block_number=head,source_block_hash=head_hash)
        if error_blocks:
            next_block=min(error_blocks);certified=next_block-1
            if certified>=self.spec.deployment_block:cb=block_cache.get(certified) or self._block(certified);self.store.set_cursor('spokepool',self.spec.chain_id,next_block,certified,cb.get('hash','') if cb else '',run_id=self.run_id)
            else:self.store.set_cursor('spokepool',self.spec.chain_id,next_block,None,None,run_id=self.run_id)
        else:self.store.set_cursor('spokepool',self.spec.chain_id,head+1,head,head_hash,run_id=self.run_id)
        self.store.bump_counter(self.run_id,'logs_seen',len(logs));self.store.bump_counter(self.run_id,'logs_accepted',accepted);gaps=self.store.unresolved_decode_gaps(self.run_id)
        return {'head':head,'from_block':start,'to_block':head,'logs':len(logs),'accepted':accepted,'errors':errors,'reorg':reorg,'cursor_next_block':self.store.get_cursor('spokepool',self.spec.chain_id,self.run_id)['next_block'],'unresolved_decode_gaps':len(gaps)}
    def run_continuous(self,stop_event,*,interval_s=2.0,max_backoff_s=30.0,on_cycle=None):
        failures=0;cycles=0
        while not stop_event.is_set():
            try:result=self.run_once();failures=0;cycles+=1;on_cycle(result) if on_cycle else None;stop_event.wait(interval_s)
            except Exception:failures+=1;stop_event.wait(min(max_backoff_s,interval_s*(2**min(failures,6))))
        return cycles
