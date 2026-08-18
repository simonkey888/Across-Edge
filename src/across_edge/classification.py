from .model import CandidateType, DepositEvent
ZERO32='0x'+'0'*64

def normalize_evm_bytes32(value:str|None)->str:
    if not value: return ZERO32
    h=value.lower().removeprefix('0x')
    if len(h)==40: h=h.rjust(64,'0')
    if len(h)!=64 or any(c not in '0123456789abcdef' for c in h):
        raise ValueError('invalid EVM address/bytes32')
    return '0x'+h

def classify_candidate(deposit:DepositEvent, relayer:str|None, destination_time:int)->CandidateType:
    exclusive=normalize_evm_bytes32(deposit.exclusive_relayer)
    if exclusive==ZERO32 or deposit.exclusivity_deadline==0: return 'open'
    if destination_time<=deposit.exclusivity_deadline:
        return 'exclusive_self' if relayer and exclusive==normalize_evm_bytes32(relayer) else 'exclusive_other'
    return 'step_in'
