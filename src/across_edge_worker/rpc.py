from __future__ import annotations
import json,ssl,urllib.error,urllib.request
from dataclasses import dataclass
from datetime import datetime,timezone
from typing import Any
from .security import assert_endpoint_allowed,endpoint_host
READ_ONLY_METHODS={"eth_chainId","eth_blockNumber","eth_getBlockByNumber","eth_getLogs","eth_call","eth_getCode","eth_getTransactionByHash","eth_getTransactionReceipt"}
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):raise ValueError("rpc_redirect_forbidden")
@dataclass(frozen=True)
class ChainEvidence:
 endpoint_host:str;chain_id:int;block_number:int;block_hash:str;as_of:str
 def to_dict(self)->dict[str,Any]:return {"endpoint_host":self.endpoint_host,"chain_id":self.chain_id,"block_number":self.block_number,"block_hash":self.block_hash,"as_of":self.as_of}
class ReadOnlyRpcClient:
 def __init__(self,url:str,allowed_urls:tuple[str,...],allowed_chain_ids:tuple[int,...],*,timeout:float=15):
  assert_endpoint_allowed(url,allowed_urls);self.url=url;self.allowed_urls=allowed_urls;self.allowed_chain_ids=set(allowed_chain_ids);self.timeout=max(.05,float(timeout));self._opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()));self.calls=0
 def call(self,method:str,params:list[Any])->Any:
  if method not in READ_ONLY_METHODS:raise PermissionError("rpc_write_or_unknown_method_forbidden:"+method)
  body=json.dumps({"jsonrpc":"2.0","id":self.calls+1,"method":method,"params":params}).encode();request=urllib.request.Request(self.url,data=body,headers={"Content-Type":"application/json","User-Agent":"across-edge-atm-worker/1.0"},method="POST")
  try:
   with self._opener.open(request,timeout=self.timeout) as response:
    if endpoint_host(response.geturl())!=endpoint_host(self.url):raise ValueError("rpc_host_changed")
    payload=json.loads(response.read())
  except urllib.error.HTTPError as exc:raise RuntimeError(f"rpc_http_error:{exc.code}") from exc
  self.calls+=1
  if not isinstance(payload,dict) or payload.get("jsonrpc")!="2.0" or "result" not in payload or payload.get("error") is not None:raise ValueError("malformed_or_error_rpc_response")
  return payload["result"]
 def chain_id(self)->int:
  result=self.call("eth_chainId",[])
  if not isinstance(result,str) or not result.startswith("0x"):raise ValueError("malformed_chain_id")
  chain_id=int(result,16)
  if chain_id not in self.allowed_chain_ids:raise ValueError("rpc_chain_id_not_allowlisted")
  return chain_id
 def provenance(self)->ChainEvidence:
  chain_id=self.chain_id();number_raw=self.call("eth_blockNumber",[])
  if not isinstance(number_raw,str) or not number_raw.startswith("0x"):raise ValueError("malformed_block_number")
  block_number=int(number_raw,16);block=self.call("eth_getBlockByNumber",[hex(block_number),False])
  if not isinstance(block,dict):raise ValueError("malformed_block")
  block_hash=block.get("hash")
  if block.get("number")!=hex(block_number) or not isinstance(block_hash,str) or len(block_hash)!=66 or not block_hash.startswith("0x"):raise ValueError("spoofed_or_malformed_block_provenance")
  return ChainEvidence(endpoint_host(self.url),chain_id,block_number,block_hash,datetime.now(timezone.utc).isoformat().replace("+00:00","Z"))
