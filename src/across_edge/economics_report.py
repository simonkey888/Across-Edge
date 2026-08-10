from __future__ import annotations
from decimal import Decimal
from .observer import percentile

def _values(rows,key):
    out=[]
    for r in rows:
        v=r.get('economics',{}).get(key)
        if v in (None,'UNKNOWN'):continue
        try:out.append(Decimal(str(v))/Decimal(10**18))
        except Exception:pass
    return out

def summarize(rows):
    keys={'gross_relayer_fee_usd':'gross_relayer_fee_usd_wei','destination_native_cost_usd':'native_token_fill_cost_usd_wei','canonical_net_relayer_fee_usd':'net_relayer_fee_usd_wei','capital_output_amount_usd':'output_amount_usd_wei'}
    result={}
    for name,key in keys.items():
        values=_values(rows,key);result[name]={'count':len(values),'p10':str(percentile(values,.1)) if values else None,'p50':str(percentile(values,.5)) if values else None,'p90':str(percentile(values,.9)) if values else None,'evidence_class':'OBSERVED_THIS_RUN'}
    result['rebalance_cost_usd']={'count':0,'p10':None,'p50':None,'p90':None,'evidence_class':'UNKNOWN_REBALANCE_DEPENDENT'}
    result['final_post_rebalance_net_usd']={'count':0,'p10':None,'p50':None,'p90':None,'evidence_class':'UNKNOWN_REBALANCE_DEPENDENT'}
    result['break_even']='UNKNOWN_REBALANCE_DEPENDENT'
    return result
