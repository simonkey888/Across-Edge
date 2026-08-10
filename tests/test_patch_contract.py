from pathlib import Path
def test_patch_has_all_canonical_stages_and_no_live_send_addition():
 p=Path('patches/across-relayer-order002-instrumentation.patch').read_text()
 for stage in ('"T0"','"T1"','"T2"','"T3"'):assert stage in p
 assert 'TransactionClient.ts' in p and 'MultiCallerClient.ts' in p and 'Relayer.ts' in p
 added='\n'.join(x[1:] for x in p.splitlines() if x.startswith('+') and not x.startswith('+++'))
 assert 'eth_sendRawTransaction' not in added and '.submit(' not in added and 'signTransaction(' not in added
 assert 'serializeTransaction' in added and 'populateTransaction' in added

def test_patch_preserves_trace_ids_through_both_bundle_paths_and_binds_economics():
 p=Path('patches/across-relayer-order002-instrumentation.patch').read_text();assert p.count('acrossEdgeTraceIds: sdkUtils.dedupArray(transactions.flatMap')==2;assert 'repaymentChainProfitability.inputAmountUsd' not in p;assert '+        inputAmountUsd,' in p

def test_patch_hunks_are_monotonic_per_file():
 import re
 p=Path('patches/across-relayer-order002-instrumentation.patch').read_text();current=None;last=-1
 for line in p.splitlines():
  if line.startswith('diff --git '):current=line;last=-1
  elif line.startswith('@@ '):
   m=re.search(r'-(\d+)',line);assert m;old=int(m.group(1));assert old>=last,(current,last,old);last=old
