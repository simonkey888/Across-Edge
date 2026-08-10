from __future__ import annotations
import json,time,urllib.request
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from dataclasses import dataclass
from .safety import assert_read_only_rpc_method,sanitize_endpoint,sanitize_text
@dataclass(frozen=True)
class RpcResult:endpoint:str;result:object;latency_ms:float
class JsonRpcClient:
    def __init__(self,endpoint:str,timeout:float=10.0):
        if not endpoint.startswith(('http://','https://')):raise ValueError('only HTTP(S) endpoints supported')
        self.endpoint=endpoint;self.timeout=timeout;self._id=0
    @property
    def label(self):return sanitize_endpoint(self.endpoint)
    def call(self,method:str,params:list|None=None)->RpcResult:
        assert_read_only_rpc_method(method);self._id+=1
        payload=json.dumps({'jsonrpc':'2.0','id':self._id,'method':method,'params':params or []}).encode()
        req=urllib.request.Request(self.endpoint,data=payload,headers={'content-type':'application/json'});start=time.perf_counter_ns()
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as resp:body=json.loads(resp.read().decode())
            if 'error' in body:raise RuntimeError(f"RPC error: {body['error']}")
            return RpcResult(self.label,body.get('result'),(time.perf_counter_ns()-start)/1_000_000)
        except Exception as e:raise RuntimeError(f'{self.label}: {sanitize_text(e)}') from None
def fallback_read(clients,method,params=None):
    errors=[]
    for c in clients:
        try:return c.call(method,params)
        except Exception as e:errors.append(sanitize_text(e))
    raise RuntimeError('all read endpoints failed: '+' | '.join(errors))
def parallel_read_race(clients,method,params=None):
    if not clients:raise ValueError('clients required')
    with ThreadPoolExecutor(max_workers=len(clients)) as ex:
        futures={ex.submit(c.call,method,params):c for c in clients};errors=[]
        while futures:
            done,_=wait(futures,return_when=FIRST_COMPLETED)
            for f in done:
                futures.pop(f,None)
                try:
                    result=f.result()
                    for pending in futures:pending.cancel()
                    return result
                except Exception as e:errors.append(sanitize_text(e))
    raise RuntimeError('all raced read endpoints failed: '+' | '.join(errors))
