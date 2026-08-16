import importlib.util,os,pytest
from pathlib import Path
from across_edge.upstream import safe_upstream_command

def load_shadow_run():
    path=Path('scripts/shadow_run.py');spec=importlib.util.spec_from_file_location('shadow_run_profile',path);module=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(module);return module

def test_runtime_profile_is_zero_write_redundant_and_bounded(monkeypatch):
    module=load_shadow_run()
    for key in list(module.os.environ):
        if any(token in key.upper() for token in ('PRIVATE_KEY','MNEMONIC','SEED_PHRASE')):monkeypatch.delenv(key,raising=False)
    env=module.runtime_env(5)
    assert env['SEND_RELAYS']=='false' and env['SEND_TRANSACTIONS']=='false' and env['SEND_SLOW_RELAYS']=='false'
    assert env['REBALANCER_ENABLED']=='false' and env['NOMINATION_WRITES_ENABLED']=='false' and env['REGISTRATION_WRITES_ENABLED']=='false'
    assert env['RELAYER_ORIGIN_CHAINS']=='[42161]' and env['RELAYER_DESTINATION_CHAINS']=='[8453]'
    assert env['RPC_PROVIDERS_1']=='M1,M2' and env['RPC_PROVIDERS_42161']=='A1,A2' and env['RPC_PROVIDERS_8453']=='B1,B2'
    assert env['MAX_BLOCK_LOOK_BACK']=='{"1":250000}' and env['NODE_MAX_CONCURRENCY']=='1'
    assert env['REDIS_URL']=='redis://127.0.0.1:6379' and env['ADDRESS_FILTER_PATH']=='./across-edge-addresses.json'
    assert env['ACROSS_EDGE_INSTRUMENTATION']=='true' and env['ACROSS_EDGE_ZERO_WRITE_SHADOW']=='true'
    assert all('eth_send' not in value.lower() for value in env.values())

def test_runtime_profile_rpc_overrides_must_be_public_keyless_https(monkeypatch):
    module=load_shadow_run();monkeypatch.setenv('ACROSS_EDGE_RPC_BASE_PRIMARY','https://example.invalid/rpc?key=secret')
    with pytest.raises(RuntimeError,match='credential-free'):module.runtime_env(5)
    monkeypatch.setenv('ACROSS_EDGE_RPC_BASE_PRIMARY','https'+chr(58)+'//'+'user'+chr(58)+'pass'+'@example.invalid/rpc')
    with pytest.raises(RuntimeError,match='credential-free'):module.runtime_env(5)

def test_upstream_safe_command_supervises_direct_canonical_entrypoint():
    cmd=safe_upstream_command('/tmp/unused')
    assert cmd[:3]==['node','./dist/index.js','--relayer']
    assert cmd[cmd.index('--wallet')+1]=='void'
    assert 'yarn' not in cmd


def test_watchdog_child_argv_matches_shadow_run_contract():
    text=Path('scripts/shadow_watchdog.py').read_text()
    assert "'--heartbeat'" not in text
    assert "'--source-head'" in text and "'--run-id'" in text and "'--db'" in text and "'--out'" in text

def test_stop_targets_watchdog_service_and_disables_restart():
    text=Path('scripts/stop_shadow.py').read_text()
    assert "service-config.json" in text and "d['enabled']=False" in text
    assert "watchdog.pid" in text and "os.killpg" in text
