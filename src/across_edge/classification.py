from .model import CandidateType, DepositEvent
ZERO32="0x"+"0"*64; ZERO20="0x"+"0"*40

def classify_candidate(deposit:DepositEvent, relayer:str|None, observed_at:int)->CandidateType:
    exclusive=deposit.exclusive_relayer.lower(); relayer_norm=(relayer or "").lower()
    if exclusive in {"",ZERO20,ZERO32} or deposit.exclusivity_deadline==0: return "open"
    if observed_at<=deposit.exclusivity_deadline:
        return "exclusive_self" if relayer_norm and exclusive.endswith(relayer_norm.removeprefix("0x")) else "exclusive_other"
    return "step_in"
