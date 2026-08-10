import pytest
from across_edge.safety import ProhibitedBroadcaster,SafetyViolation,assert_read_only_rpc_method,validate_shadow_environment

def test_shadow_env_accepts_void_and_false_flags(): assert validate_shadow_environment({"SEND_RELAYS":"false","SEND_TRANSACTIONS":"false"},["--wallet","void"]).wallet_type=="void"
def test_true_send_relays_fails_closed():
    with pytest.raises(SafetyViolation,match="LIVE_EXECUTION_PROHIBITED"):validate_shadow_environment({"SEND_RELAYS":"true"},["--wallet","void"])
def test_private_key_fails_closed():
    with pytest.raises(SafetyViolation,match="forbids real secret"):validate_shadow_environment({"PRIVATE_KEY":"placeholder-but-present"},["--wallet","void"])
def test_non_void_wallet_fails_closed():
    with pytest.raises(SafetyViolation):validate_shadow_environment({},["--wallet","secret"])
def test_rpc_write_method_blocked():
    with pytest.raises(SafetyViolation):assert_read_only_rpc_method("eth_sendRawTransaction")
    assert_read_only_rpc_method("eth_getLogs")
def test_broadcaster_is_permanent_stub():
    with pytest.raises(SafetyViolation,match="LIVE_EXECUTION_PROHIBITED"):ProhibitedBroadcaster().broadcast(b"x")
