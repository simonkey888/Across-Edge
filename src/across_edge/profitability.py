from decimal import Decimal,ROUND_CEILING
from .model import PnlInput
EVIDENCE_CLASSES={'OBSERVED_THIS_RUN','PRIMARY_SOURCE','DERIVED_CALCULATION','ASSUMPTION','HISTORICAL_PRIOR_RESEARCH','UNKNOWN'}
def net_before_infra(p:PnlInput)->Decimal|None:
    vals=[p.gross_relayer_fee_usd,p.destination_gas_usd,p.protocol_lp_fee_usd,p.rebalance_cost_usd]
    if any(v is None for v in vals):return None
    return p.gross_relayer_fee_usd-p.destination_gas_usd-p.protocol_lp_fee_usd-p.rebalance_cost_usd
def break_even_fills(monthly_fixed_cost_usd:Decimal,net_per_fill_usd:Decimal|None)->int|None:
    if monthly_fixed_cost_usd==0:return 0 if net_per_fill_usd and net_per_fill_usd>0 else None
    if net_per_fill_usd is None or net_per_fill_usd<=0:return None
    return int((monthly_fixed_cost_usd/net_per_fill_usd).to_integral_value(rounding=ROUND_CEILING))
def scenario_table(net_per_fill_usd:Decimal|None,costs=('0','5','10','20')):return [{'monthly_fixed_cost_usd':c,'break_even_fills':break_even_fills(Decimal(c),net_per_fill_usd)} for c in costs]
def normalize_canonical_economics(raw:dict)->dict:
    def dec18(name):
        v=raw.get(name)
        if v in (None,'UNKNOWN'):return None
        return Decimal(str(v))/Decimal(10**18)
    gross=dec18('gross_relayer_fee_usd_wei');gas=dec18('native_token_fill_cost_usd_wei');net=dec18('net_relayer_fee_usd_wei');capital=dec18('output_amount_usd_wei')
    return {'gross_relayer_fee_usd':gross,'destination_native_cost_usd':gas,'canonical_net_relayer_fee_usd':net,'capital_required_usd':capital,'repayment_chain_id':raw.get('repayment_chain_id'),'rebalance_cost_usd':None,'rebalance_cost_evidence':'UNKNOWN'}
