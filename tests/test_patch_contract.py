from pathlib import Path
def patch():return Path('patches/across-relayer-order003-instrumentation.patch').read_text()
def test_patch_has_all_stages_and_no_live_send_addition():
 p=patch()
 for stage in ('"T0"','"TA"','"T1"','"T2"','"T3"'):assert stage in p
 added='\n'.join(x[1:] for x in p.splitlines() if x.startswith('+') and not x.startswith('+++'));assert 'eth_sendRawTransaction' not in added and '.submit(' not in added and 'signTransaction(' not in added;assert 'serializeTransaction' in added and 'populateTransaction' in added
def test_patch_models_confirmation_gate_and_suppresses_early_trace():
 p=patch();assert 'deposit.blockNumber <= maxBlockNumber' in p;assert 'simulation_early_not_live_actionable' in p;assert 'acrossEdgeLiveActionable ? acrossEdgeTrace : undefined' in p;assert 'emitAcrossEdge("TA"' in p
def test_trace_ids_preserved_through_both_bundle_paths():assert patch().count('acrossEdgeTraceIds: sdkUtils.dedupArray(transactions.flatMap')==2
def test_patch_economics_binding_uses_canonical_profit_fields():
 p=patch();assert 'grossRelayerFeeUsd' in p and 'nativeTokenFillCostUsd' in p and 'netRelayerFeeUsd' in p
