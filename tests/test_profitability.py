from decimal import Decimal
from across_edge.profitability import normalize_canonical_economics,scenario_table
def test_canonical_units_and_unknown_rebalance():
 x=normalize_canonical_economics({'gross_relayer_fee_usd_wei':'2000000000000000000','native_token_fill_cost_usd_wei':'500000000000000000','net_relayer_fee_usd_wei':'1500000000000000000','output_amount_usd_wei':'100000000000000000000','repayment_chain_id':8453});assert x['canonical_net_relayer_fee_usd']==Decimal('1.5') and x['rebalance_cost_usd'] is None
 assert scenario_table(Decimal('1'))[1]['break_even_fills']==5
