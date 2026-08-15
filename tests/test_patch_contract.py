import re
from pathlib import Path

PATCH_PATH = Path('patches/across-relayer-order003-instrumentation.patch')


def patch():
    return PATCH_PATH.read_text()


def production_additions(p: str) -> str:
    production = p.split('diff --git a/test/', 1)[0]
    return '\n'.join(line[1:] for line in production.splitlines() if line.startswith('+') and not line.startswith('+++'))


def test_patch_has_all_stages_and_no_live_send_addition():
    p = patch()
    for stage in ('"T0"', '"TA"', '"T1"', '"T2"', '"T3"'):
        assert stage in p
    added = production_additions(p)
    assert 'eth_sendRawTransaction' not in added
    assert '.submit(' not in added
    assert 'signTransaction(' not in added
    assert 'sendTransaction(' not in added
    assert 'serializeTransaction' in added
    assert 'populateTransaction' in added


def test_patch_models_confirmation_gate_and_suppresses_early_trace():
    p = patch()
    assert 'deposit.blockNumber <= maxBlockNumber' in p
    assert 'simulation_early_not_live_actionable' in p
    assert 'acrossEdgeLiveActionable ? acrossEdgeTrace : undefined' in p
    assert 'emitAcrossEdge("TA"' in p


def test_trace_ids_preserved_through_both_bundle_paths():
    assert patch().count('acrossEdgeTraceIds: sdkUtils.dedupArray(transactions.flatMap') == 2


def test_t3_prepare_uses_explicit_ethers_unsigned_transaction_and_safe_nonce():
    added = production_additions(patch())
    assert 'const populated: ethers.providers.TransactionRequest' in added
    assert 'const unsigned: ethers.utils.UnsignedTransaction' in added
    assert 'BigNumber.from(complete.nonce)' in added
    assert 'Number.MAX_SAFE_INTEGER' in added
    assert 'nonce exceeds JS safe integer range' in added
    assert 'ethers.utils.serializeTransaction(unsigned)' in added
    assert 'from:' not in '\n'.join(line for line in added.splitlines() if 'const unsigned:' in line)


def test_patch_economics_binding_uses_optional_canonical_profit_fields():
    p = patch()
    assert 'diff --git a/src/clients/ProfitClient.ts' in p
    assert 'Partial<' in p
    assert 'await this.getFillProfitability(deposit, lpFeePct, repaymentChainId)' in p
    for field in (
        'inputAmountUsd',
        'outputAmountUsd',
        'grossRelayerFeeUsd',
        'nativeTokenFillCostUsd',
        'netRelayerFeeUsd',
    ):
        assert field in p
    assert '?? "UNKNOWN"' in p


def test_repayment_profitability_helper_return_type_carries_observed_economics():
    p = patch()
    helper_hunk = p.split('@@ -1422,5 +1501,10 @@', 1)[1].split('@@ -1430,12 +1514,22 @@', 1)[0]
    for field in (
        'inputAmountUsd?: BigNumber;',
        'outputAmountUsd?: BigNumber;',
        'grossRelayerFeeUsd?: BigNumber;',
        'nativeTokenFillCostUsd?: BigNumber;',
        'netRelayerFeeUsd?: BigNumber;',
    ):
        assert field in helper_hunk


def test_patch_contains_runtime_regressions_for_unsigned_prepare_and_economics():
    p = patch()
    assert 'Prepares deterministic unsigned transaction without signing or sending' in p
    assert 'Fails closed when a populated nonce exceeds the JS safe integer range' in p
    assert 'Exposes observed profitability economics and leaves failed observations undefined' in p
    assert 'expect(signTransaction.called).to.be.false' in p
    assert 'expect(sendTransaction.called).to.be.false' in p


def test_transaction_client_import_hunk_has_normal_context_for_plain_git_apply():
    p = patch()
    assert '@@ -10,1 +10,1 @@' not in p
    assert '@@ -10,7 +10,7 @@' in p
    assert ' import { CHAIN_ID_TEST_LIST as chainIds } from "./constants";' in p
    assert ' const { spyLogger }: { spyLogger: winston.Logger } = createSpyLogger();' in p


def test_patch_hunk_headers_match_payload_counts_and_require_context():
    lines = patch().splitlines()
    for i, line in enumerate(lines):
        if not line.startswith('@@'):
            continue
        match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
        assert match, f'invalid hunk header: {line}'
        expected_old = int(match.group(2) or 1)
        expected_new = int(match.group(4) or 1)
        old_count = new_count = context_count = 0
        j = i + 1
        while j < len(lines) and not lines[j].startswith('@@') and not lines[j].startswith('diff --git '):
            payload = lines[j]
            if payload == '':
                next_nonempty = next((lines[k] for k in range(j + 1, len(lines)) if lines[k]), None)
                if next_nonempty and next_nonempty.startswith('diff --git '):
                    j += 1
                    continue
                raise AssertionError(f'empty unprefixed line inside hunk after: {line}')
            if payload.startswith('\\ No newline at end of file'):
                j += 1
                continue
            assert payload[0] in ' +-', f'invalid hunk payload line: {payload!r}'
            if payload[0] in ' -':
                old_count += 1
            if payload[0] in ' +':
                new_count += 1
            if payload[0] == ' ':
                context_count += 1
            j += 1
        assert (old_count, new_count) == (expected_old, expected_new), (
            line,
            old_count,
            new_count,
            expected_old,
            expected_new,
        )
        assert context_count > 0, f'zero-context hunk is incompatible with canonical plain git apply: {line}'
