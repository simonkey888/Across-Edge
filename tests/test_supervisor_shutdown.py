import os,subprocess,sys,threading,time
from across_edge.supervisor import ContinuousSupervisor

class SlowObserver:
    def __init__(self):self.exited=threading.Event();self.closed=False
    def run_once(self):time.sleep(.25);self.exited.set();return {}
    def close(self):self.closed=True
class Coordinator:
    def ingest_line(self,_line):pass

def test_supervisor_waits_for_observer_threads_before_returning():
    observer=SlowObserver()
    def proc():return subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],stdout=subprocess.PIPE,text=True,start_new_session=True)
    sup=ContinuousSupervisor(coordinator=Coordinator(),observers=[observer],process_factory=proc,observer_interval_s=.01)
    sup.run(threading.Event(),max_runtime_s=.05)
    assert observer.exited.is_set() and observer.closed
    assert not any(t.name.startswith('across-edge-observer-') and t.is_alive() for t in threading.enumerate())

def test_supervisor_terminates_complete_descendant_process_group(tmp_path):
    child_file=tmp_path/'child.pid'
    code=("import subprocess,sys,time;"
          "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
          f"open({str(child_file)!r},'w').write(str(p.pid));"
          "time.sleep(60)")
    def proc():return subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,text=True,start_new_session=True)
    sup=ContinuousSupervisor(coordinator=Coordinator(),observers=[SlowObserver()],process_factory=proc,observer_interval_s=.01)
    sup.run(threading.Event(),max_runtime_s=.15)
    for _ in range(50):
        if child_file.exists():break
        time.sleep(.02)
    assert child_file.exists();pid=int(child_file.read_text())
    for _ in range(50):
        try:os.kill(pid,0)
        except ProcessLookupError:break
        time.sleep(.02)
    else:raise AssertionError('orphan descendant remained after supervisor shutdown')
