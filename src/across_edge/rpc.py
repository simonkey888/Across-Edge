import json,time,urllib.request
from dataclasses import dataclass
from .safety import assert_read_only_rpc_method
@dataclass(frozen=True)
class RpcResult: endpoint:str; result:object; latency_ms:float
class JsonRpcClient:
    def __init__(self,endpoint:str,timeout:float=10.0):
        if not endpoint.startswith(("http://","https://")):raise ValueError("only HTTP(S) endpoints supported")
        self.endpoint=endpoint;self.timeout=timeout;self._id=0
    def call(self,method:str,params:list|None=None)->RpcResult:
        assert_read_only_rpc_method(method);self._id+=1;payload=json.dumps({"jsonrpc":"2.0","id":self._id,"method":method,"params":params or []}).encode();req=urllib.request.Request(self.endpoint,data=payload,headers={"content-type":"application/json"});start=time.perf_counter_ns()
        with urllib.request.urlopen(req,timeout=self.timeout) as resp: body=json.loads(resp.read().decode())
        if "error" in body:raise RuntimeError(f"RPC error: {body['error']}")
        return RpcResult(self.endpoint,body.get("result"),(time.perf_counter_ns()-start)/1_000_000)

def hedged_read(clients,method,params=None):
    errors=[]
    for c in clients:
        try:return c.call(method,params)
        except Exception as e:errors.append(f"{c.endpoint}: {e}")
    raise RuntimeError("all read endpoints failed: "+" | ".join(errors))
