from types import SimpleNamespace
from across_edge.chain_observer import ChainSpec,RpcObserver
from across_edge.evm import FUNDS_DEPOSITED_TOPIC0
from across_edge.storage import Store
from conftest import make_deposit
class FakeRpc:
 def __init__(self,logs,head=10):self.logs=logs;self.head=head
 def call(self,m,p=None):
  if m=='eth_blockNumber':return SimpleNamespace(result=hex(self.head))
  if m=='eth_getLogs':return SimpleNamespace(result=self.logs)
  if m=='eth_getBlockByNumber':
   n=int(p[0],16);return SimpleNamespace(result={'hash':f'0xb{n}','timestamp':hex(100+n)})
  raise AssertionError(m)
def log(block=9):return {'blockNumber':hex(block),'blockHash':f'0xb{block}','transactionHash':'0xabc','logIndex':'0x1','topics':[FUNDS_DEPOSITED_TOPIC0,'0x'+hex(8453)[2:].rjust(64,'0'),'0x'+hex(7)[2:].rjust(64,'0'),'0x'+'1'*64],'data':'0x'}
def test_decode_failure_does_not_certify_range_and_recovers_on_retry(tmp_path):
 s=Store(tmp_path/'x');calls={'n':0}
 def decoder(raw,**kw):
  calls['n']+=1
  if calls['n']==1:raise ValueError('future ABI')
  return make_deposit(block=9,ts=109,tx='0xabc')
 obs=RpcObserver(s,'r',ChainSpec(42161,'arb','http://fake','0xspoke'),rpc=FakeRpc([log()]),decode_deposit=decoder)
 first=obs.run_once();assert first['errors']==1 and first['cursor_next_block']==9;g=s.unresolved_decode_gaps('r');assert len(g)==1 and g[0]['block_number']==9 and g[0]['retry_count']==1
 second=obs.run_once();assert second['errors']==0 and second['cursor_next_block']==11 and not s.unresolved_decode_gaps('r');assert len(s.all_deposits())==1;s.close()
def test_malformed_log_survives_restart_as_gap(tmp_path):
 p=tmp_path/'x';s=Store(p);obs=RpcObserver(s,'r',ChainSpec(42161,'arb','http://fake','0xspoke'),rpc=FakeRpc([log()]),decode_deposit=lambda *_a,**_k:(_ for _ in ()).throw(RuntimeError('bad')));obs.run_once();s.close();s=Store(p);assert s.unresolved_decode_gaps('r')[0]['error_class']=='RuntimeError';s.close()
