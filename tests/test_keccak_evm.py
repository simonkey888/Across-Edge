from across_edge.keccak import keccak256
from across_edge.evm import FUNDS_DEPOSITED_TOPIC0,FILLED_RELAY_TOPIC0
def test_keccak_empty_vector():assert keccak256(b'').hex()=='c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'
def test_event_topics_are_32_bytes():assert len(FUNDS_DEPOSITED_TOPIC0)==66 and len(FILLED_RELAY_TOPIC0)==66 and FUNDS_DEPOSITED_TOPIC0!=FILLED_RELAY_TOPIC0
