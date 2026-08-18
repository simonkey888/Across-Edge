import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'config/upstream-pin.json').read_text())
PATCH = ROOT / MANIFEST['instrumentation_patch']
TEST_PATCH = ROOT / MANIFEST['upstream_test_patch']


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def changed_paths(path: Path) -> list[str]:
    text = path.read_text()
    return re.findall(r'^diff --git a/(\S+) b/\1$', text, flags=re.M)


def test_runtime_binary_patch_is_sha_bound_and_pinned():
    assert MANIFEST['sha'] == '741ca9f7d72923f7b13c1c2462ca90eba81e1a87'
    assert sha256(PATCH) == MANIFEST['instrumentation_patch_sha256']
    assert MANIFEST['send_relays'] is False
    assert MANIFEST['send_transactions'] is False
    assert MANIFEST['safe_cli'][-2:] == ['--wallet', 'void']


def test_runtime_binary_patch_covers_only_required_upstream_source_files():
    assert 'GIT binary patch' in PATCH.read_text()
    assert changed_paths(PATCH) == [
        'src/adapter/l2Bridges/BinanceCEXBridge.ts',
        'src/clients/MultiCallerClient.ts',
        'src/clients/ProfitClient.ts',
        'src/clients/TransactionClient.ts',
        'src/rebalancer/RebalancerClientHelper.ts',
        'src/relayer/Relayer.ts',
        'src/relayer/RelayerClientHelper.ts',
    ]


def test_runtime_patch_cannot_smuggle_env_workflow_or_dependency_files():
    paths = changed_paths(PATCH)
    assert all(p.startswith('src/') for p in paths)
    assert not any('.env' in p or p.startswith('.github/') or p.endswith(('package.json','yarn.lock','package-lock.json')) for p in paths)


def test_upstream_regression_overlay_is_separately_sha_bound():
    assert sha256(TEST_PATCH) == MANIFEST['upstream_test_patch_sha256']
    assert 'GIT binary patch' in TEST_PATCH.read_text()
    assert changed_paths(TEST_PATCH) == [
        'test/ProfitClient.ConsiderProfitability.ts',
        'test/TransactionClient.ts',
    ]


def test_patch_headers_bind_full_pre_and_post_image_object_ids():
    for path in (PATCH, TEST_PATCH):
        text = path.read_text()
        headers = re.findall(r'^index ([0-9a-f]{40})\.\.([0-9a-f]{40}) 100644$', text, flags=re.M)
        assert headers
        assert len(headers) == len(changed_paths(path))
