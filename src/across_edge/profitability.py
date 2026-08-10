from decimal import Decimal
from .model import PnlInput

def net_before_infra(p:PnlInput)->Decimal|None:
    vals=[p.gross_relayer_fee_usd,p.destination_gas_usd,p.protocol_lp_fee_usd,p.rebalance_cost_usd]
    if any(v is None for v in vals): return None
    return p.gross_relayer_fee_usd-p.destination_gas_usd-p.protocol_lp_fee_usd-p.rebalance_cost_usd

def break_even_fills(monthly_fixed_cost_usd:Decimal,net_per_fill_usd:Decimal|None)->int|None:
    if net_per_fill_usd is None or net_per_fill_usd<=0:return None
    return int((monthly_fixed_cost_usd/net_per_fill_usd).to_integral_value(rounding="ROUND_CEILING"))

def scenario_table(net_per_fill_usd:Decimal|None,costs=("0","5","10","20")):
    return [{"monthly_fixed_cost_usd":c,"break_even_fills":break_even_fills(Decimal(c),net_per_fill_usd)} for c in costs]
