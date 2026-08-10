from pathlib import Path
def test_patch_has_all_canonical_stages_and_no_live_send_addition():
 p=Path('patches/across-relayer-order002-instrumentation.patch').read_text()
 for stage in ('"T0"','"T1"','"T2"','"T3"'):assert stage in p
 assert 'TransactionClient.ts' in p and 'MultiCallerClient.ts' in p and 'Relayer.ts' in p
 added='\n'.join(x[1:] for x in p.splitlines() if x.startswith('+') and not x.startswith('+++'))
 assert 'eth_sendRawTransaction' not in added and '.submit(' not in added and 'signTransaction(' not in added
 assert 'serializeTransaction' in added and 'populateTransaction' in added
