import json,subprocess,sys,threading
from across_edge.coordinator import ShadowCoordinator,PREFIX
from across_edge.storage import Store
from across_edge.supervisor import ContinuousSupervisor
class Obs:
 def __init__(self):self.n=0
 def run_once(self):self.n+=1;return {'cycle':self.n}
def line(stage,**kw):
 d={'version':3,'stage':stage,'trace_id':'tr','deposit_key':'42161:1','origin_chain_id':42161,'deposit_id':1,'destination_chain_id':8453,'candidate_type':'other','deposit_block':1,'source_monotonic_ns':'1'};d.update(kw);return PREFIX+json.dumps(d)
def test_supervisor_runs_multiple_cycles_and_clean_shutdown(tmp_path):
 s=Store(tmp_path/'x');c=ShadowCoordinator(s,'r');payload='\n'.join([line('T0',max_block_number=1,live_equivalent_confirmations_satisfied=True),line('TA',max_block_number=1,live_equivalent_confirmations_satisfied=True),line('T1',eligible=True,profitability_decision='profitable'),line('T2',simulation_result='success'),line('T3',transaction_ready=True,transaction_serialized='0x00')]);code=f"import time;print({payload!r},flush=True);time.sleep(5)"
 def spawn():return subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 obs=Obs();sup=ContinuousSupervisor(coordinator=c,observers=[obs],process_factory=spawn,observer_interval_s=.02);res=sup.run(threading.Event(),max_runtime_s=1.5);assert res.status=='PASS' and obs.n>=2 and s.shadow_by_trace('r','tr')['transaction_ready'] is True;s.close()
def test_observer_restart_continuity_is_state_external_to_supervisor(tmp_path):
 s=Store(tmp_path/'x');s.set_cursor('spokepool',8453,11,10,'0xb10');s.close();s=Store(tmp_path/'x');assert s.get_cursor('spokepool',8453)['next_block']==11;s.close()
def test_read_only_relayer_child_is_restarted_with_bound(tmp_path):
 s=Store(tmp_path/'y');c=ShadowCoordinator(s,'r');calls={'n':0}
 def spawn():
  calls['n']+=1;code="import time;time.sleep(.05)" if calls['n']==1 else "import time;time.sleep(5)";return subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 sup=ContinuousSupervisor(coordinator=c,observers=[Obs()],process_factory=spawn,observer_interval_s=.02,restart_delay_s=.02,max_relayer_restarts=2);res=sup.run(threading.Event(),max_runtime_s=1.8);assert calls['n']>=2 and res.relayer_restarts==1 and res.status=='PASS';s.close()
