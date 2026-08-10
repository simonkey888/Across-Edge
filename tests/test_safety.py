import pytest
from across_edge.safety import *
def test_void_false_flags_pass():assert validate_shadow_environment({'SEND_RELAYS':'false','RELAYER_USE_INVENTORY_MANAGER':'false'},['--wallet','void']).wallet_type=='void'
@pytest.mark.parametrize('flag',['SEND_RELAYS','SEND_TRANSACTIONS','SEND_SLOW_RELAYS','RELAYER_USE_INVENTORY_MANAGER','EXECUTOR_ENABLED','REBALANCER_ENABLED','NOMINATION_WRITES_ENABLED','REGISTRATION_WRITES_ENABLED'])
def test_all_execution_flags_fail_closed(flag):
 with pytest.raises(SafetyViolation):validate_shadow_environment({flag:'true'},['--wallet','void'])
def test_keys_nonvoid_write_rpc_and_broadcaster_blocked():
 with pytest.raises(SafetyViolation):validate_shadow_environment({'PRIVATE_KEY':'x'},['--wallet','void'])
 with pytest.raises(SafetyViolation):validate_shadow_environment({},['--wallet','secret'])
 for m in ['eth_sendRawTransaction','eth_sendTransaction','personal_sendTransaction']:
  with pytest.raises(SafetyViolation):assert_read_only_rpc_method(m)
 with pytest.raises(SafetyViolation):ProhibitedBroadcaster().broadcast(b'x')
def test_sanitizer_redacts_url_and_tokens():
 text=sanitize_text('https'+chr(58)+'//'+'user'+chr(58)+'pass'+'@example.com/rpc?key=abcdef Authorization: '+'Bearer '+'abcdefghijklmnop')
 assert 'user' not in text and 'pass' not in text and 'key=' not in text and 'abcdefghijklmnop' not in text;assert 'https://example.com/rpc' in text
