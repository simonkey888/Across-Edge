from across_edge.model import DepositEvent,FillEvent

def make_deposit(*,origin=42161,dest=8453,deposit_id=7,exclusive='0x'+'0'*64,deadline=0,block=10,ts=100,tx='0xdep'):
    return DepositEvent(origin,dest,deposit_id,'0x'+'1'*64,'0x'+'2'*64,'0x'+'3'*64,'0x'+'4'*64,1000,990,exclusive,deadline,999999,block,tx,ts,block_hash='0xblock',log_index=1)
def make_fill(*,origin=42161,dest=8453,deposit_id=7,rel='0x'+'5'*64,block=12,ts=102,tx='0xf1',idx=2,fill_type=0,observed=None):
    return FillEvent(origin,dest,deposit_id,rel,origin,block,tx,ts,fill_type,'0xfblock',idx,observed,'2026-08-10T00:00:00Z' if observed is not None else None)
