from __future__ import annotations
import json
import os
import subprocess
import time
from pathlib import Path
import pytest
from across_edge.atm_worker import InjectedCrash, WorkerCannotHandle, WorkerContractError, WorkerExecutionError, WorkerJob, compute_scope_hash, decode_event_fixture, reconcile_relayer_fixture, run_worker_job, sanitized_worker_env, scan_generated_artifacts, validate_unsigned_transaction, verify_fee_logic, verify_rpc_response
from across_edge.safety import SafetyViolation
SOURCE_SHA = '1' * 40
ARBITRUM_RPC = 'https://arb1.arbitrum.io/rpc'
BASE_RPC = 'https://mainnet.base.org'
BLOCK_HASH = '0x' + 'ab' * 32

def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(['git', '-C', str(cwd), *args], text=True, capture_output=True, check=True)
    return proc.stdout.strip()

def make_target(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / 'target-source'
    root.mkdir()
    _git(root, 'init')
    _git(root, 'config', 'user.email', 'worker@example.invalid')
    _git(root, 'config', 'user.name', 'Worker Fixture')
    (root / 'client.py').write_text('TIMEOUT = 5\n', encoding='utf-8')
    (root / 'README.md').write_text('fixture\n', encoding='utf-8')
    _git(root, 'add', 'client.py', 'README.md')
    _git(root, 'commit', '-m', 'fixture')
    return (root, _git(root, 'rev-parse', 'HEAD'))

def raw_job(target_sha: str, *, actions=None, checks=None, expires_delta: int=3600):
    raw = {'job_id': 'job-001', 'canonical_opportunity_id': 'opp-001', 'worker_id': 'across-edge', 'work_lease_id': 'lease-001', 'scope_hash': '', 'lease_state': 'active', 'lease_expires_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + expires_delta)), 'frozen_acceptance_criteria': ['repair is deterministic', 'no external mutation'], 'target_repository': 'fixture://sdk-client', 'target_base_sha': target_sha, 'allowed_paths': ['client.py'], 'required_capabilities': ['sdk_client_repair', 'fee_logic_verification', 'unsigned_transaction_validation', 'event_log_decoding', 'relayer_reconciliation', 'chain_provenance', 'external_mutation_refusal'], 'structured_requirements': {'actions': actions or []}, 'expected_deliverable': {'kind': 'patch+report'}, 'deterministic_checks': checks or [], 'allowed_chain_ids': [42161, 8453], 'allowed_read_endpoints': {'42161': [ARBITRUM_RPC], '8453': [BASE_RPC]}, 'max_spend_usd': 0}
    raw['scope_hash'] = compute_scope_hash(raw)
    return raw

def test_contract_binds_scope_lease_worker_spend_and_authority(tmp_path: Path):
    _, sha = make_target(tmp_path)
    raw = raw_job(sha)
    job = WorkerJob.from_mapping(raw)
    assert job.worker_id == 'across-edge'
    assert job.max_spend_usd == 0
    bad = dict(raw, worker_id='other')
    bad['scope_hash'] = compute_scope_hash(bad)
    with pytest.raises(WorkerContractError, match='worker_id mismatch'):
        WorkerJob.from_mapping(bad)
    bad = dict(raw, max_spend_usd='0.01')
    bad['scope_hash'] = compute_scope_hash(bad)
    with pytest.raises(WorkerContractError, match='nonzero spend'):
        WorkerJob.from_mapping(bad)
    bad = dict(raw, scope_hash='0' * 64)
    with pytest.raises(WorkerContractError, match='scope_hash mismatch'):
        WorkerJob.from_mapping(bad)
    expired = raw_job(sha, expires_delta=-1)
    with pytest.raises(WorkerContractError, match='lease expired'):
        WorkerJob.from_mapping(expired)
    mutation = raw_job(sha, actions=[{'capability': 'external_mutation_refusal', 'operation': 'broadcast'}])
    with pytest.raises(WorkerCannotHandle, match='CANNOT_HANDLE'):
        WorkerJob.from_mapping(mutation)

def test_worker_environment_strips_ambient_credentials():
    env = sanitized_worker_env({'PATH': os.environ.get('PATH', ''), 'AWS_SECRET_ACCESS_KEY': 'do-not-copy', 'PAYMENT_TOKEN': 'do-not-copy', 'PRIVATE_KEY': 'do-not-copy', 'HOME': '/host/home'}, home='/tmp/worker-home')
    assert 'AWS_SECRET_ACCESS_KEY' not in env
    assert 'PAYMENT_TOKEN' not in env
    assert 'PRIVATE_KEY' not in env
    assert env['HOME'] == '/tmp/worker-home'
    assert env['SEND_RELAYS'] == 'false'
    assert env['SEND_TRANSACTIONS'] == 'false'
    assert env['GIT_CONFIG_KEY_0'] == 'core.hooksPath'

def test_unsigned_transaction_is_data_only_and_chain_bounded(tmp_path: Path):
    _, sha = make_target(tmp_path)
    job = WorkerJob.from_mapping(raw_job(sha))
    good = validate_unsigned_transaction(job, {'chain_id': 42161, 'to': '0x' + '12' * 20, 'data': '0x1234', 'value': 0})
    assert good['external_execution'] is False
    assert good['signature_present'] is False
    with pytest.raises(WorkerContractError, match='signed/secret'):
        validate_unsigned_transaction(job, {'chain_id': 42161, 'to': '0x' + '12' * 20, 'data': '0x', 'value': 0, 'signature': '0x01'})
    with pytest.raises(WorkerContractError, match='chain is not allowed'):
        validate_unsigned_transaction(job, {'chain_id': 1, 'to': '0x' + '12' * 20, 'data': '0x', 'value': 0})

def test_event_decoder_and_relayer_reconciliation_are_fixture_only():
    schema = {'name': 'FilledRelay', 'inputs': [{'name': 'depositor', 'type': 'address', 'indexed': True}, {'name': 'amount', 'type': 'uint256', 'indexed': False}]}
    topic0 = '0x' + '11' * 32
    depositor = bytes.fromhex('00' * 12 + '22' * 20).hex()
    amount = 123 .to_bytes(32, 'big').hex()
    decoded = decode_event_fixture(schema, {'topics': [topic0, '0x' + depositor], 'data': '0x' + amount})
    assert decoded['decoded']['depositor'] == '0x' + '22' * 20
    assert decoded['decoded']['amount'] == 123
    report = reconcile_relayer_fixture([{'origin_chain_id': 42161, 'deposit_id': '1'}, {'origin_chain_id': 42161, 'deposit_id': '2'}], [{'origin_chain_id': 42161, 'deposit_id': '1'}, {'origin_chain_id': 42161, 'deposit_id': '1'}])
    assert report['duplicate_fill_count'] == 1
    assert report['unfilled'] == [{'origin_chain_id': 42161, 'deposit_id': '2'}]
    assert report['external_execution'] is False

def test_fee_verification_never_claims_realized_profit():
    result = verify_fee_logic({'gross_relayer_fee_usd': '2.5', 'gas_usd': '0.3', 'bridge_fee_usd': '0.2', 'slippage_usd': '0.1'})
    assert result['net_ev_usd'] == '1.9'
    assert result['profitable'] is True
    assert result['realized_profit_claimed'] is False

def test_rpc_evidence_requires_allowlisted_read_method_chain_endpoint_and_block(tmp_path: Path):
    _, sha = make_target(tmp_path)
    job = WorkerJob.from_mapping(raw_job(sha))
    evidence = verify_rpc_response(job, chain_id=42161, endpoint=ARBITRUM_RPC, method='eth_getLogs', response={'jsonrpc': '2.0', 'id': 1, 'result': []}, block_number=123, block_hash=BLOCK_HASH, observed_at='2026-08-18T09:00:00Z')
    assert evidence['read_only'] is True
    assert evidence['block_number'] == 123
    with pytest.raises(WorkerContractError, match='outside frozen allowlist'):
        verify_rpc_response(job, chain_id=1, endpoint='https://example.invalid/rpc', method='eth_getLogs', response={'jsonrpc': '2.0', 'id': 1, 'result': []}, block_number=1, block_hash=BLOCK_HASH)
    with pytest.raises(SafetyViolation):
        verify_rpc_response(job, chain_id=42161, endpoint=ARBITRUM_RPC, method='eth_sendRawTransaction', response={'jsonrpc': '2.0', 'id': 1, 'result': '0x0'}, block_number=1, block_hash=BLOCK_HASH)
    with pytest.raises(WorkerExecutionError, match='malformed/spoofed'):
        verify_rpc_response(job, chain_id=42161, endpoint=ARBITRUM_RPC, method='eth_getLogs', response={'jsonrpc': '1.0', 'result': []}, block_number=1, block_hash=BLOCK_HASH)

def test_full_lifecycle_repairs_isolated_target_and_emits_hashed_result(tmp_path: Path):
    target, sha = make_target(tmp_path)
    actions = [{'capability': 'sdk_client_repair', 'operation': 'replace_text', 'path': 'client.py', 'old': 'TIMEOUT = 5', 'new': 'TIMEOUT = 10'}, {'capability': 'fee_logic_verification', 'operation': 'verify', 'inputs': {'gross_relayer_fee_usd': '2', 'gas_usd': '0.5', 'bridge_fee_usd': '0.2', 'slippage_usd': '0.1'}}, {'capability': 'external_mutation_refusal', 'operation': 'verify_refusal', 'requested_operation': 'broadcast'}]
    raw = raw_job(sha, actions=actions, checks=[{'kind': 'file_contains', 'path': 'client.py', 'text': 'TIMEOUT = 10'}, {'kind': 'artifact_exists', 'path': 'worker.patch'}])
    result = run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=tmp_path / 'run', canonical_checkout=tmp_path / 'canonical-across-edge')
    assert result['status'] == 'RESULT_READY'
    assert result['outgoing_spend_usd'] == '0'
    assert result['financial_authority'] == 0
    assert result['external_protocol_mutation_authority'] == 0
    assert 'worker.patch' in result['artifact_hashes']
    assert result['patch_sha256'] == result['artifact_hashes']['worker.patch']
    assert (tmp_path / 'run' / 'state' / 'ack.json').is_file()
    assert (tmp_path / 'run' / 'state' / 'events.jsonl').read_text().count('"event":"PROGRESS"') >= 2
    assert (target / 'client.py').read_text() == 'TIMEOUT = 5\n'
    isolated = tmp_path / 'run' / 'workspace' / 'target-job-001' / 'client.py'
    assert isolated.read_text() == 'TIMEOUT = 10\n'

def test_restart_after_ack_does_not_duplicate_result_or_target_mutation(tmp_path: Path):
    target, sha = make_target(tmp_path)
    actions = [{'capability': 'sdk_client_repair', 'operation': 'replace_text', 'path': 'client.py', 'old': 'TIMEOUT = 5', 'new': 'TIMEOUT = 10'}]
    raw = raw_job(sha, actions=actions, checks=[{'kind': 'file_contains', 'path': 'client.py', 'text': 'TIMEOUT = 10'}])
    run_root = tmp_path / 'run'
    with pytest.raises(InjectedCrash, match='after_ack'):
        run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=run_root, crash_at='after_ack')
    result = run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=run_root)
    assert result['status'] == 'RESULT_READY'
    events = (run_root / 'state' / 'events.jsonl').read_text().splitlines()
    assert sum((json.loads(line)['event'] == 'ACK' for line in events)) == 1

def test_restart_after_target_write_recognizes_already_applied_mutation(tmp_path: Path):
    target, sha = make_target(tmp_path)
    actions = [{'capability': 'sdk_client_repair', 'operation': 'replace_text', 'path': 'client.py', 'old': 'TIMEOUT = 5', 'new': 'TIMEOUT = 10'}]
    raw = raw_job(sha, actions=actions, checks=[{'kind': 'file_contains', 'path': 'client.py', 'text': 'TIMEOUT = 10'}])
    run_root = tmp_path / 'run'
    with pytest.raises(InjectedCrash, match='after_target_write:0'):
        run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=run_root, crash_at='after_target_write:0')
    result = run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=run_root)
    assert result['status'] == 'RESULT_READY'
    isolated = run_root / 'workspace' / 'target-job-001' / 'client.py'
    assert isolated.read_text().count('TIMEOUT = 10') == 1

def test_restart_after_artifact_creation_reuses_action_receipts(tmp_path: Path):
    target, sha = make_target(tmp_path)
    actions = [{'capability': 'fee_logic_verification', 'operation': 'verify', 'inputs': {'gross_relayer_fee_usd': '1', 'gas_usd': '0.1', 'bridge_fee_usd': '0.1', 'slippage_usd': '0.1'}}]
    raw = raw_job(sha, actions=actions, checks=[{'kind': 'artifact_exists', 'path': 'worker.patch'}])
    run_root = tmp_path / 'run'
    with pytest.raises(InjectedCrash, match='after_result_artifact'):
        run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=run_root, crash_at='after_result_artifact')
    result = run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=run_root)
    assert result['status'] == 'RESULT_READY'
    actions_dir = run_root / 'state' / 'actions'
    assert len(list(actions_dir.glob('*.json'))) == 1

def test_symlink_target_surface_is_rejected(tmp_path: Path):
    target, sha = make_target(tmp_path)
    (target / 'escape').symlink_to(tmp_path)
    raw = raw_job(sha)
    with pytest.raises(WorkerExecutionError, match='symlink target surface rejected'):
        run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=tmp_path / 'run')

def test_cli_capabilities_is_non_economic(capsys):
    from across_edge.atm_worker_cli import main
    assert main(['capabilities']) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['worker_id'] == 'across-edge'
    assert payload['financial_authority'] == 0
    assert payload['external_protocol_mutation_authority'] == 0
    assert 'chain_provenance' in payload['capabilities']

def test_rpc_client_rejects_redirects_and_spoofed_chain(tmp_path: Path):
    from across_edge.atm_worker import ReadOnlyRpcClient, WorkerExecutionError
    _, sha = make_target(tmp_path)
    job = WorkerJob.from_mapping(raw_job(sha))
    def good_transport(method, params):
        if method == 'eth_chainId':
            return ({'jsonrpc': '2.0', 'id': 1, 'result': hex(42161)}, ARBITRUM_RPC)
        if method == 'eth_getBlockByNumber':
            return ({'jsonrpc': '2.0', 'id': 1, 'result': {'number': hex(100), 'hash': BLOCK_HASH}}, ARBITRUM_RPC)
        return ({'jsonrpc': '2.0', 'id': 1, 'result': []}, ARBITRUM_RPC)
    response, evidence = ReadOnlyRpcClient(job, 42161, ARBITRUM_RPC, transport=good_transport).query('eth_getLogs', [])
    assert response['result'] == []
    assert evidence['chain_id'] == 42161
    def redirect_transport(method, params):
        return ({'jsonrpc': '2.0', 'id': 1, 'result': hex(42161)}, 'https://evil.invalid/rpc')
    with pytest.raises(WorkerExecutionError, match='redirect/host change'):
        ReadOnlyRpcClient(job, 42161, ARBITRUM_RPC, transport=redirect_transport).query('eth_getLogs', [])
    def wrong_chain(method, params):
        if method == 'eth_chainId':
            return ({'jsonrpc': '2.0', 'id': 1, 'result': hex(1)}, ARBITRUM_RPC)
        return ({'jsonrpc': '2.0', 'id': 1, 'result': []}, ARBITRUM_RPC)
    with pytest.raises(WorkerExecutionError, match='chain mismatch'):
        ReadOnlyRpcClient(job, 42161, ARBITRUM_RPC, transport=wrong_chain).query('eth_getLogs', [])

def test_durable_cancellation_and_timeout_fail_closed(tmp_path: Path):
    from across_edge.atm_worker import ExecutionJournal, WorkerCancelled
    target, sha = make_target(tmp_path)
    actions = [{'capability': 'fee_logic_verification', 'operation': 'verify', 'inputs': {'gross_relayer_fee_usd': '1', 'gas_usd': '0.1', 'bridge_fee_usd': '0.1', 'slippage_usd': '0.1'}}]
    raw = raw_job(sha, actions=actions)
    run_root = tmp_path / 'cancel-run'
    job = WorkerJob.from_mapping(raw)
    journal = ExecutionJournal(run_root / 'state', job, SOURCE_SHA)
    journal.request_cancel()
    with pytest.raises(WorkerCancelled, match='cancellation'):
        run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=run_root)
    assert '"event":"CANCELLED"' in (run_root / 'state' / 'events.jsonl').read_text()
    timeout_raw = raw_job(sha, actions=actions)
    timeout_raw['structured_requirements'] = dict(timeout_raw['structured_requirements'], max_runtime_seconds=1e-12)
    timeout_raw['scope_hash'] = compute_scope_hash(timeout_raw)
    with pytest.raises(WorkerExecutionError, match='timeout exceeded'):
        run_worker_job(timeout_raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=tmp_path / 'timeout-run')

def test_cli_cancel_creates_durable_marker(tmp_path: Path, capsys):
    from across_edge.atm_worker_cli import main
    root = tmp_path / 'job'
    assert main(['cancel', '--run-root', str(root)]) == 0
    assert (root / 'state' / 'cancel.requested').read_text() == 'requested\n'
    assert json.loads(capsys.readouterr().out)['status'] == 'CANCEL_REQUESTED'

def test_real_world_shadow_op_deployer_calldata_spec_can_handle_read_only(tmp_path: Path):
    root = tmp_path / 'op-target'
    root.mkdir()
    _git(root, 'init')
    _git(root, 'config', 'user.email', 'worker@example.invalid')
    _git(root, 'config', 'user.name', 'Worker Fixture')
    (root / 'manager.py').write_text('SUPERCHAIN_CONFIG_SLOT = None\n', encoding='utf-8')
    _git(root, 'add', 'manager.py')
    _git(root, 'commit', '-m', 'op-deployer fixture')
    _git(root, 'remote', 'add', 'origin', 'https://github.com/ethereum-optimism/optimism.git')
    sha = _git(root, 'rev-parse', 'HEAD')
    actions = [{'capability': 'sdk_client_repair', 'operation': 'replace_text', 'path': 'manager.py', 'old': 'SUPERCHAIN_CONFIG_SLOT = None', 'new': 'SUPERCHAIN_CONFIG_SLOT = 108'}, {'capability': 'unsigned_transaction_validation', 'operation': 'validate', 'transaction': {'chain_id': 42161, 'to': '0x' + '10' * 20, 'data': '0x1234', 'value': 0}}, {'capability': 'unsigned_transaction_validation', 'operation': 'validate', 'transaction': {'chain_id': 42161, 'to': '0x' + '20' * 20, 'data': '0xabcd', 'value': 0}}, {'capability': 'unsigned_transaction_validation', 'operation': 'validate', 'transaction': {'chain_id': 42161, 'to': '0x' + '10' * 20, 'data': '0x5678', 'value': 0}}, {'capability': 'chain_provenance', 'operation': 'verify', 'chain_id': 42161, 'endpoint': ARBITRUM_RPC, 'method': 'eth_call', 'response': {'jsonrpc': '2.0', 'id': 1, 'result': '0x' + '00' * 12 + '33' * 20}, 'block_number': 123456, 'block_hash': BLOCK_HASH, 'observed_at': '2026-08-18T09:27:00Z'}]
    raw = raw_job(sha, actions=actions, checks=[{'kind': 'file_contains', 'path': 'manager.py', 'text': 'SUPERCHAIN_CONFIG_SLOT = 108'}, {'kind': 'artifact_exists', 'path': 'worker.patch'}])
    raw['target_repository'] = 'https://github.com/ethereum-optimism/optimism'
    raw['allowed_paths'] = ['manager.py']
    raw['scope_hash'] = compute_scope_hash(raw)
    result = run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=root, run_root=tmp_path / 'op-shadow')
    assert result['status'] == 'RESULT_READY'
    assert len(result['chain_evidence_refs']) == 1
    assert result['chain_evidence_refs'][0]['read_only'] is True
    assert result['external_protocol_mutation_authority'] == 0

def test_real_world_shadow_base_mainnet_deployment_reproduction_is_cannot_handle(tmp_path: Path):
    _, sha = make_target(tmp_path)
    raw = raw_job(sha, actions=[{'capability': 'external_mutation_refusal', 'operation': 'deploy_contract', 'external_mutation': True}])
    with pytest.raises(WorkerCannotHandle, match='CANNOT_HANDLE_UNDER_CURRENT_AUTHORITY'):
        WorkerJob.from_mapping(raw)

def test_target_repository_origin_binding_and_generated_secret_scan(tmp_path: Path):
    target, sha = make_target(tmp_path)
    raw = raw_job(sha)
    raw['target_repository'] = 'https://github.com/example/expected'
    raw['scope_hash'] = compute_scope_hash(raw)
    with pytest.raises(WorkerContractError, match='no verifiable origin|does not match'):
        run_worker_job(raw, worker_source_sha=SOURCE_SHA, target_source_checkout=target, run_root=tmp_path / 'bad-origin')
    artifacts = tmp_path / 'artifacts'
    artifacts.mkdir()
    (artifacts / 'safe.txt').write_text('read-only evidence\n', encoding='utf-8')
    assert scan_generated_artifacts(artifacts)['status'] == 'PASS'
    (artifacts / 'bad.txt').write_text('Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\n', encoding='utf-8')
    with pytest.raises(WorkerExecutionError, match='secret scan rejected'):
        scan_generated_artifacts(artifacts)
