from __future__ import annotations
import difflib,json,re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from .lifecycle import LifecycleStore
from .rpc import ReadOnlyRpcClient
from .security import sha256_file,validate_relative_path
TRANSFER_TOPIC="0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; ADDRESS=re.compile(r"^0x[0-9a-fA-F]{40}$"); HEX_DATA=re.compile(r"^0x(?:[0-9a-fA-F]{2})*$")
@dataclass
class CapabilityContext:
    target:Path; allowed_paths:tuple[str,...]; store:LifecycleStore; execution_id:str; allowed_endpoints:tuple[str,...]; allowed_chain_ids:tuple[int,...]
def decode_transfer_log(log:dict[str,Any])->dict[str,Any]:
    topics=log.get("topics"); data=log.get("data")
    if not isinstance(topics,list) or len(topics)!=3 or str(topics[0]).lower()!=TRANSFER_TOPIC: raise ValueError("unsupported_or_malformed_event_log")
    if not all(isinstance(t,str) and t.startswith("0x") and len(t)==66 for t in topics): raise ValueError("malformed_event_topics")
    if not isinstance(data,str) or not data.startswith("0x") or len(data)!=66: raise ValueError("malformed_event_data")
    return {"event":"Transfer(address,address,uint256)","from":"0x"+topics[1][-40:],"to":"0x"+topics[2][-40:],"value":int(data,16),"block_number":int(str(log.get("blockNumber","0x0")),16),"block_hash":str(log.get("blockHash") or "")}
def chain_provenance(ctx,action):
    endpoint=str(action["endpoint"]); expected=int(action["chain_id"]); key=f"chain-provenance:{expected}:{endpoint}"; request={"endpoint":endpoint,"chain_id":expected,"methods":["eth_chainId","eth_blockNumber","eth_getBlockByNumber"]}; cached=ctx.store.cached_read(ctx.execution_id,key,request)
    if cached is not None:return cached
    evidence=ReadOnlyRpcClient(endpoint,ctx.allowed_endpoints,ctx.allowed_chain_ids).provenance().to_dict()
    if evidence["chain_id"]!=expected:raise ValueError("chain_provenance_mismatch")
    ctx.store.record_read(ctx.execution_id,key,request,evidence); return evidence
def apply_text_repair(ctx,action):
    relative=str(action["path"]); path=validate_relative_path(ctx.target,relative,ctx.allowed_paths,must_exist=True); before=path.read_text(); old=str(action["old"]); new=str(action["new"]); key=f"repair:{relative}:{action.get('repair_id','default')}"; payload={"path":relative,"before_hash":sha256_file(path),"before_text":before,"old":old,"new":new}; existing=[r for r in ctx.store.list_receipts(ctx.execution_id) if r["receipt_key"]==key]; original=before
    if existing:
        original=str(existing[0]["payload"]["before_text"]); expected=original.replace(old,new,1)
        if before==original:pass
        elif before==expected:
            patch="".join(difflib.unified_diff(original.splitlines(keepends=True),expected.splitlines(keepends=True),fromfile=f"a/{relative}",tofile=f"b/{relative}")); return {"path":relative,"status":"APPLIED","after_hash":sha256_file(path),"patch":patch}
        else:raise ValueError("repair_recovery_state_ambiguous")
    else:ctx.store.receipt(ctx.execution_id,key,"MUTATION_INTENT",payload)
    count=original.count(old)
    if count!=1:raise ValueError(f"repair_match_count_invalid:{count}")
    after=original.replace(old,new,1); path.write_text(after); patch="".join(difflib.unified_diff(original.splitlines(keepends=True),after.splitlines(keepends=True),fromfile=f"a/{relative}",tofile=f"b/{relative}")); return {"path":relative,"status":"APPLIED","after_hash":sha256_file(path),"patch":patch}
def validate_unsigned_transaction(tx,allowed_chain_ids):
    if any(k in tx for k in ("signature","r","s","v","rawTransaction","signedTransaction")):raise ValueError("signed_transaction_material_forbidden")
    chain_id=int(tx.get("chain_id",-1)); to=str(tx.get("to") or ""); data=str(tx.get("data") or ""); value=int(tx.get("value",0))
    if chain_id not in set(allowed_chain_ids):raise ValueError("unsigned_tx_chain_not_allowed")
    if not ADDRESS.match(to) or not HEX_DATA.match(data) or value<0:raise ValueError("unsigned_transaction_structure_invalid")
    return {"status":"VALID_AS_DATA_ONLY","chain_id":chain_id,"to":to.lower(),"data_bytes":(len(data)-2)//2,"value":value,"executed":False,"signed":False}
def reconcile_attempts(attempts):
    best={}; ambiguous=set()
    for row in attempts:
        key=(str(row.get("deposit_id") or ""),str(row.get("evaluation_id") or ""))
        if not all(key):raise ValueError("reconciliation_identity_missing")
        score=sum(row.get(f) is not None for f in ("observed_at","decision","block_hash","net_fee_wei"))
        if key in best and best[key].get("decision") not in {None,row.get("decision")} and row.get("decision") is not None:ambiguous.add(key)
        if key not in best or score>best[key]["_score"]:best[key]={**row,"_score":score}
    rows=[]
    for key,row in sorted(best.items()): clean={k:v for k,v in row.items() if k!="_score"};clean["ambiguous"]=key in ambiguous;rows.append(clean)
    return {"deduped_count":len(rows),"ambiguous_count":len(ambiguous),"rows":rows}
def verify_fee_logic(inputs):
    req=("gross_fee_wei","gas_cost_wei","capital_cost_wei","rebalance_cost_wei")
    if any(k not in inputs for k in req):raise ValueError("fee_inputs_missing")
    vals={k:int(inputs[k]) for k in req}
    if any(v<0 for v in vals.values()):raise ValueError("fee_input_negative")
    net=vals["gross_fee_wei"]-vals["gas_cost_wei"]-vals["capital_cost_wei"]-vals["rebalance_cost_wei"]
    return {"inputs":vals,"net_fee_wei":net,"net_fee_native_decimal":str(Decimal(net)/Decimal(10**18)),"classification":"DERIVED_PINNED_INPUTS","realized_profit":False,"external_acceptance":False}
def static_check(ctx,check):
    kind=str(check.get("kind") or ""); relative=str(check.get("path") or ""); path=validate_relative_path(ctx.target,relative,ctx.allowed_paths,must_exist=True)
    if kind=="file_contains":passed=str(check.get("needle") or "") in path.read_text()
    elif kind=="file_not_contains":passed=str(check.get("needle") or "") not in path.read_text()
    elif kind=="json_parse":json.loads(path.read_text());passed=True
    else:raise ValueError("unsupported_deterministic_check")
    if not passed:raise AssertionError(f"deterministic_check_failed:{kind}:{relative}")
    return {"kind":kind,"path":relative,"passed":True}
