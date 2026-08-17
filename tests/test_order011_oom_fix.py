from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_order011_bounds_bootstrap_without_increasing_heap_or_tuning_economics():
    source = (ROOT / "scripts/order011_shadow_run.py").read_text()
    assert "LOOKBACK_SECONDS = 3600" in source
    assert "RESTART_BUDGET = 3" in source
    assert "HEAP_LIMIT_MB = 768" in source
    assert 'MAX_RELAYER_DEPOSIT_LOOK_BACK' in source
    assert "--max-old-space-size={HEAP_LIMIT_MB}" in source
    forbidden = ("profitability_threshold", "min_profit", "fee_threshold", "economic_threshold")
    assert all(token not in source.lower() for token in forbidden)


def test_order011_instruments_start_and_end_memory_per_loop_fail_closed():
    source = (ROOT / "scripts/order011_upstream_fix.py").read_text()
    assert source.count('message: "ACROSS_EDGE_MEMORY"') == 2
    assert 'phase: "start"' in source
    assert 'phase: "end"' in source
    for field in ("heapUsed", "heapTotal", "rss", "loopCount"):
        assert source.count(field) >= 2
    assert "pinned upstream loop anchors changed; refusing fuzzy instrumentation" in source
    assert "partial ORDER-011 memory instrumentation detected" in source


def test_order011_keeps_terminal_safety_contract_in_base_runner():
    base = (ROOT / "scripts/shadow_run.py").read_text()
    for literal in (
        "'SEND_RELAYS':'false'",
        "'SEND_TRANSACTIONS':'false'",
        "'NOMINATION_WRITES_ENABLED':'false'",
        "'REGISTRATION_WRITES_ENABLED':'false'",
        "['--wallet','void']",
    ):
        assert literal in base
