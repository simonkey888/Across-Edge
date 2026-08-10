from across_edge.classification import classify_candidate,normalize_evm_bytes32
from across_edge.model import DepositEvent
def dep(exclusive,deadline):return DepositEvent(42161,8453,7,'0x'+'1'*64,'0x'+'2'*64,'0x'+'3'*64,'0x'+'4'*64,1,1,exclusive,deadline,999,1,'0xd',100)
def test_deadline_boundaries_and_address_normalization():
 a='0x'+'a'*40;d=dep(normalize_evm_bytes32(a),200)
 assert classify_candidate(d,None,199)=='exclusive_other';assert classify_candidate(d,None,200)=='exclusive_other';assert classify_candidate(d,None,201)=='step_in';assert classify_candidate(d,a,200)=='exclusive_self'
def test_zero_is_open():assert classify_candidate(dep('0x'+'0'*64,200),None,100)=='open'
