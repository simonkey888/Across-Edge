from across_edge.rpc import fallback_read,parallel_read_race,RpcResult
class C:
 def __init__(self,name,result=None,error=None):self.endpoint='https://'+name+'.example/?token=secret';self.name=name;self.result=result;self.error=error
 def call(self,m,p=None):
  if self.error:raise RuntimeError(self.error)
  return RpcResult('https://'+self.name+'.example/',self.result,1)
def test_sequential_fallback_is_honestly_named():assert fallback_read([C('a',error='x'),C('b',result=2)],'eth_blockNumber').result==2
def test_parallel_read_race_is_read_only_experiment():assert parallel_read_race([C('a',error='x'),C('b',result=2)],'eth_blockNumber').result==2
