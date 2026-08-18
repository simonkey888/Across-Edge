from __future__ import annotations
import hashlib,json
MATERIAL_FIELDS=('origin_chain_id','destination_chain_id','deposit_id','input_token','output_token','input_amount','output_amount','recipient','message','fill_deadline','exclusive_relayer','exclusivity_deadline','updated_output_amount','updated_recipient','updated_message','speed_up_signature','update_authorization')
OPTIONAL_UPDATE_FIELDS=('updated_output_amount','updated_recipient','updated_message','speed_up_signature','update_authorization')
def canonical_version_fields(event:dict)->dict:
    supplied=event.get('deposit_version_fields')
    if isinstance(supplied,dict):return {k:supplied[k] for k in sorted(supplied)}
    return {k:event[k] for k in MATERIAL_FIELDS if k in event}
def deposit_version_identity(event:dict,attempt_nonce:str)->tuple[str,str,str,dict]:
    fields=canonical_version_fields(event);encoded=json.dumps(fields,sort_keys=True,separators=(',',':'),default=str);fp=hashlib.sha256(encoded.encode()).hexdigest()
    complete=all(k in fields for k in OPTIONAL_UPDATE_FIELDS)
    provenance='COMPLETE' if complete else 'PARTIAL_UNKNOWN_UPDATE_PROVENANCE'
    version_id=f"v:{fp[:32]}" if complete else f"v:unknown:{attempt_nonce}"
    return version_id,fp,provenance,fields
