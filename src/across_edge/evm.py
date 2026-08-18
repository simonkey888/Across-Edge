from __future__ import annotations
from typing import Any
from .keccak import keccak256
from .model import DepositEvent,FillEvent
FUNDS_DEPOSITED_SIGNATURE='FundsDeposited(bytes32,bytes32,uint256,uint256,uint256,uint256,uint32,uint32,uint32,bytes32,bytes32,bytes32,bytes)'
FILLED_RELAY_SIGNATURE='FilledRelay(bytes32,bytes32,uint256,uint256,uint256,uint256,uint256,uint32,uint32,bytes32,bytes32,bytes32,bytes32,bytes32,(bytes32,bytes32,uint256,uint8))'
FUNDS_DEPOSITED_TOPIC0='0x'+keccak256(FUNDS_DEPOSITED_SIGNATURE.encode()).hex();FILLED_RELAY_TOPIC0='0x'+keccak256(FILLED_RELAY_SIGNATURE.encode()).hex()
def _words(data_hex:str)->list[str]:
    h=data_hex.removeprefix('0x')
    if len(h)%64:raise ValueError('ABI data is not word aligned')
    return [h[i:i+64] for i in range(0,len(h),64)]
def _u(word:str)->int:return int(word,16)
def _b32(word:str)->str:return '0x'+word.lower().rjust(64,'0')
def _topic_u(topic:str)->int:return int(topic,16)
def _block_number(log):return int(log['blockNumber'],16) if isinstance(log['blockNumber'],str) else int(log['blockNumber'])
def _log_index(log):
    v=log.get('logIndex',-1);return int(v,16) if isinstance(v,str) else int(v)
def decode_funds_deposited(log:dict[str,Any],*,origin_chain_id:int,block_timestamp:int)->DepositEvent:
    topics=log['topics']
    if topics[0].lower()!=FUNDS_DEPOSITED_TOPIC0.lower():raise ValueError('not FundsDeposited')
    if len(topics)!=4:raise ValueError('FundsDeposited requires 3 indexed arguments')
    w=_words(log['data'])
    if len(w)<10:raise ValueError('FundsDeposited data too short')
    return DepositEvent(origin_chain_id,_topic_u(topics[1]),_topic_u(topics[2]),_b32(topics[3].removeprefix('0x')),_b32(w[7]),_b32(w[0]),_b32(w[1]),_u(w[2]),_u(w[3]),_b32(w[8]),_u(w[6]),_u(w[5]),_block_number(log),log['transactionHash'],block_timestamp,log.get('blockHash',''),_log_index(log))
def decode_filled_relay(log:dict[str,Any],*,destination_chain_id:int,block_timestamp:int)->FillEvent:
    topics=log['topics']
    if topics[0].lower()!=FILLED_RELAY_TOPIC0.lower():raise ValueError('not FilledRelay')
    if len(topics)!=4:raise ValueError('FilledRelay requires 3 indexed arguments')
    w=_words(log['data'])
    if len(w)<15:raise ValueError('FilledRelay data too short')
    return FillEvent(_topic_u(topics[1]),destination_chain_id,_topic_u(topics[2]),_b32(topics[3].removeprefix('0x')),_u(w[4]),_block_number(log),log['transactionHash'],block_timestamp,_u(w[14]),log.get('blockHash',''),_log_index(log))
