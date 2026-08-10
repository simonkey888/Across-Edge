from __future__ import annotations
from dataclasses import dataclass
from .evm import FUNDS_DEPOSITED_TOPIC0,FILLED_RELAY_TOPIC0,decode_funds_deposited,decode_filled_relay
from .observer import Observer
from .rpc import JsonRpcClient
from .storage import Store
@dataclass(frozen=True)
class ChainSpec:
    chain_id:int;name:str;rpc_url:str;spoke_pool:str;deployment_block:int=0
class RpcObserver:
    def __init__(self,store:Store,run_id:str,spec:ChainSpec,relayer_address:str|None=None,backfill_blocks:int=256,reorg_depth:int=32):
        self.store=store;self.run_id=run_id;self.spec=spec;self.rpc=JsonRpcClient(spec.rpc_url);self.observer=Observer(store,relayer_address);self.backfill_blocks=backfill_blocks;self.reorg_depth=reorg_depth
    def _block(self,n:int):return self.rpc.call('eth_getBlockByNumber',[hex(n),False]).result
    def run_once(self)->dict:
        head=int(self.rpc.call('eth_blockNumber').result,16);cursor=self.store.get_cursor('spokepool',self.spec.chain_id);reorg=False
        if cursor and cursor['last_block_number'] is not None:
            prior=self._block(cursor['last_block_number'])
            if prior and cursor['last_block_hash'] and prior.get('hash','').lower()!=cursor['last_block_hash'].lower():
                rewind=max(self.spec.deployment_block,cursor['last_block_number']-self.reorg_depth+1);self.store.rewind_chain(self.spec.chain_id,rewind);cursor=None;reorg=True;self.store.bump_counter(self.run_id,'reorgs_detected')
                start=rewind
            else:start=cursor['next_block']
        else:start=max(self.spec.deployment_block,head-self.backfill_blocks+1)
        if start>head:return {'head':head,'from_block':start,'to_block':head,'logs':0,'reorg':reorg}
        params=[{'address':self.spec.spoke_pool,'fromBlock':hex(start),'toBlock':hex(head),'topics':[[FUNDS_DEPOSITED_TOPIC0,FILLED_RELAY_TOPIC0]]}]
        logs=self.rpc.call('eth_getLogs',params).result or [];block_cache={};accepted=0;errors=0
        for log in sorted(logs,key=lambda x:(int(x['blockNumber'],16),int(x.get('logIndex','0x0'),16))):
            bn=int(log['blockNumber'],16)
            if bn not in block_cache:block_cache[bn]=self._block(bn)
            ts=int(block_cache[bn]['timestamp'],16);topic=log['topics'][0].lower()
            try:
                if topic==FUNDS_DEPOSITED_TOPIC0.lower():
                    d=decode_funds_deposited(log,origin_chain_id=self.spec.chain_id,block_timestamp=ts);self.observer.ingest_deposit(d,self.run_id);accepted+=1
                elif topic==FILLED_RELAY_TOPIC0.lower():
                    f=decode_filled_relay(log,destination_chain_id=self.spec.chain_id,block_timestamp=ts);self.observer.ingest_fill(f,self.run_id);accepted+=1
            except Exception:
                errors+=1;self.store.bump_counter(self.run_id,'decode_errors')
        head_block=block_cache.get(head) or self._block(head);head_hash=head_block.get('hash','') if head_block else '';head_ts=int(head_block['timestamp'],16) if head_block else 0
        self.observer.refresh_candidate_states(self.run_id,self.spec.chain_id,head_ts)
        self.store.set_cursor('spokepool',self.spec.chain_id,head+1,head,head_hash);self.store.bump_counter(self.run_id,'logs_seen',len(logs));self.store.bump_counter(self.run_id,'logs_accepted',accepted)
        return {'head':head,'from_block':start,'to_block':head,'logs':len(logs),'accepted':accepted,'errors':errors,'reorg':reorg}
