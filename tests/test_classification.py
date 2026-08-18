from across_edge.classification import classify_candidate,normalize_evm_bytes32
from conftest import make_deposit
def test_deadline_boundaries_and_address_normalization():
 a='0x'+'a'*40;d=make_deposit(exclusive=normalize_evm_bytes32(a),deadline=200)
 assert classify_candidate(d,None,199)=='exclusive_other';assert classify_candidate(d,None,200)=='exclusive_other';assert classify_candidate(d,None,201)=='step_in';assert classify_candidate(d,a,200)=='exclusive_self'
def test_zero_is_open():assert classify_candidate(make_deposit(exclusive='0x'+'0'*64,deadline=200),None,100)=='open'
