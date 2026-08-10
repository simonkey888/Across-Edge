from __future__ import annotations
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Literal

CandidateType=Literal['open','exclusive_other','exclusive_self','step_in','other']

@dataclass(frozen=True)
class DepositEvent:
    origin_chain_id:int; destination_chain_id:int; deposit_id:int; depositor:str; recipient:str
    input_token:str; output_token:str; input_amount:int; output_amount:int; exclusive_relayer:str
    exclusivity_deadline:int; fill_deadline:int; block_number:int; tx_hash:str; block_timestamp:int
    block_hash:str=''; log_index:int=-1
    @property
    def key(self)->str: return f'{self.origin_chain_id}:{self.deposit_id}'
    @property
    def event_id(self)->str: return f'{self.tx_hash.lower()}:{self.log_index}'

@dataclass(frozen=True)
class FillEvent:
    origin_chain_id:int; destination_chain_id:int; deposit_id:int; relayer:str; repayment_chain_id:int
    block_number:int; tx_hash:str; block_timestamp:int; fill_type:int=0; block_hash:str=''; log_index:int=-1
    @property
    def key(self)->str: return f'{self.origin_chain_id}:{self.deposit_id}'
    @property
    def event_id(self)->str: return f'{self.tx_hash.lower()}:{self.log_index}'

@dataclass
class ShadowRecord:
    schema_version:int; run_id:str; deposit_key:str; origin_chain_id:int; deposit_id:int; destination_chain_id:int
    input_token:str; output_token:str; input_amount:int; output_amount:int; exclusive_relayer:str
    exclusivity_deadline:int; candidate_type:CandidateType
    trace_id:str=''; t0_monotonic_ns:int|None=None; t1_monotonic_ns:int|None=None; t2_monotonic_ns:int|None=None; t3_monotonic_ns:int|None=None
    t0_wall_utc:str|None=None; t1_wall_utc:str|None=None; t2_wall_utc:str|None=None; t3_wall_utc:str|None=None
    decision_destination_time:int|None=None; eligible:bool|None=None; profitability_decision:str='UNKNOWN'
    estimated_relayer_fee:str='UNKNOWN'; estimated_gas:str='UNKNOWN'; estimated_rebalance_cost:str='UNKNOWN'; estimated_net:str='UNKNOWN'
    simulation_result:str='UNKNOWN'; transaction_ready:bool|None=None; rejection_reason:str=''
    transaction_serialized:str=''; economics:dict[str,Any]=field(default_factory=dict); evidence_classes:dict[str,str]=field(default_factory=dict)
    winner_relayer:str=''; winner_tx_hash:str=''; winner_block:int|None=None; tw_wall_utc:str|None=None; tw_monotonic_ns:int|None=None
    winner_latency_ms:float|None=None; shadow_headroom_ms:float|None=None; candidate_state_history:list[dict[str,Any]]=field(default_factory=list)
    def as_dict(self)->dict[str,Any]: return asdict(self)

@dataclass(frozen=True)
class PnlInput:
    gross_relayer_fee_usd:Decimal|None; destination_gas_usd:Decimal|None; protocol_lp_fee_usd:Decimal|None
    rebalance_cost_usd:Decimal|None; capital_required_usd:Decimal|None
