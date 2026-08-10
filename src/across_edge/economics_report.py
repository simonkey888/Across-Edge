from __future__ import annotations
from collections import Counter
from decimal import Decimal
from .observer import percentile

def _values(rows,key,scale=10**18):
    out=[]
    for r in rows:
        v=r.get('economics',{}).get(key)
        if v in (None,'UNKNOWN'):continue
        try:out.append(Decimal(str(v))/Decimal(scale))
        except Exception:pass
    return out

def _summary(values,evidence_class='OBSERVED_THIS_RUN'):
    n=len(values)
    return {'count':n,'p10':str(percentile(values,.1)) if n>=2 else None,'p50':str(percentile(values,.5)) if n>=1 else None,'p90':str(percentile(values,.9)) if n>=2 else None,'evidence_class':evidence_class,'sample_status':'OK' if n>=2 else ('SAMPLE_INSUFFICIENT' if n==1 else 'NO_SAMPLE')}

def summarize(rows):
    keys={'gross_relayer_fee_usd':'gross_relayer_fee_usd_wei','destination_native_cost_usd':'native_token_fill_cost_usd_wei','canonical_net_relayer_fee_usd':'net_relayer_fee_usd_wei','capital_output_amount_usd':'output_amount_usd_wei'}
    result={name:_summary(_values(rows,key)) for name,key in keys.items()}
    lp=[]
    for r in rows:
        v=r.get('economics',{}).get('lp_fee_pct')
        if v not in (None,'UNKNOWN'):
            try:lp.append(Decimal(str(v)))
            except Exception:pass
    result['lp_fee_pct']=_summary(lp)
    repayment=Counter(str(r.get('economics',{}).get('repayment_chain_id')) for r in rows if r.get('economics',{}).get('repayment_chain_id') not in (None,'UNKNOWN'))
    result['repayment_chain_counts']=dict(sorted(repayment.items()))
    decisions=Counter(str(r.get('profitability_decision','UNKNOWN')) for r in rows if r.get('profitability_decision') not in (None,''))
    result['profitability_decision_counts']=dict(sorted(decisions.items()))
    result['rebalance_cost_usd']={'count':0,'p10':None,'p50':None,'p90':None,'evidence_class':'UNKNOWN_REBALANCE_DEPENDENT','sample_status':'UNKNOWN_EXTERNAL'}
    result['final_post_rebalance_net_usd']={'count':0,'p10':None,'p50':None,'p90':None,'evidence_class':'UNKNOWN_REBALANCE_DEPENDENT','sample_status':'UNKNOWN_EXTERNAL'}
    result['break_even']='UNKNOWN_REBALANCE_DEPENDENT'
    return result
