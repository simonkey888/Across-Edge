from __future__ import annotations
import queue,threading,time
from dataclasses import dataclass,field
from .safety import sanitize_text
@dataclass
class ComponentState:cycles:int=0;restarts:int=0;last_success_monotonic_ns:int|None=None;last_error:str='';alive:bool=False
@dataclass
class SupervisorResult:status:str;runtime_monotonic_ns:int;relayer_returncode:int|None;observer_cycles:int;relayer_restarts:int;errors:list[str]=field(default_factory=list)
class ContinuousSupervisor:
    def __init__(self,*,coordinator,observers,process_factory,observer_interval_s:float=2.0,restart_delay_s:float=1.0,max_relayer_restarts:int=3,periodic=None,periodic_interval_s:float=60.0):self.coordinator=coordinator;self.observers=list(observers);self.process_factory=process_factory;self.observer_interval_s=max(.01,observer_interval_s);self.restart_delay_s=max(.01,restart_delay_s);self.max_relayer_restarts=max(0,max_relayer_restarts);self.periodic=periodic;self.periodic_interval_s=max(.05,periodic_interval_s);self.states={f'observer:{i}':ComponentState() for i in range(len(self.observers))};self.states['relayer']=ComponentState()
    @staticmethod
    def _err(errors,msg):errors.append(msg);errors[:]=errors[-100:]
    def health(self):return {'ready':self.states['relayer'].alive and all(v.alive for k,v in self.states.items() if k.startswith('observer:')),'components':{k:vars(v).copy() for k,v in self.states.items()}}
    def _observer_worker(self,idx,observer,stop_event,errors):
        state=self.states[f'observer:{idx}'];state.alive=True;failures=0
        while not stop_event.is_set():
            try:observer.run_once();state.cycles+=1;state.last_success_monotonic_ns=time.perf_counter_ns();state.last_error='';failures=0;stop_event.wait(self.observer_interval_s)
            except Exception as exc:state.last_error=sanitize_text(exc);self._err(errors,f'observer:{idx}:{state.last_error}');failures+=1;state.restarts+=1;stop_event.wait(min(30.0,self.observer_interval_s*(2**min(failures,6))))
        state.alive=False
    @staticmethod
    def _reader(proc,outq):
        try:
            if proc.stdout:
                for line in proc.stdout:outq.put(line.rstrip('\n'))
        finally:outq.put(None)
    def _spawn(self):
        proc=self.process_factory();self.states['relayer'].alive=True;outq=queue.Queue();reader=threading.Thread(target=self._reader,args=(proc,outq),daemon=True);reader.start();return proc,outq,reader
    def run(self,stop_event,*,max_runtime_s:float|None=None)->SupervisorResult:
        start=time.perf_counter_ns();errors=[];threads=[]
        for idx,obs in enumerate(self.observers):
            t=threading.Thread(target=self._observer_worker,args=(idx,obs,stop_event,errors),daemon=True);t.start();threads.append(t)
        proc,outq,reader=self._spawn();next_periodic=time.monotonic()+self.periodic_interval_s;terminal_rc=None
        try:
            while not stop_event.is_set():
                if max_runtime_s is not None and (time.perf_counter_ns()-start)/1e9>=max_runtime_s:stop_event.set();break
                try:item=outq.get(timeout=.05)
                except queue.Empty:item='__NO_LINE__'
                if item is None or proc.poll() is not None:
                    terminal_rc=proc.poll();self.states['relayer'].alive=False
                    if stop_event.is_set():break
                    if self.states['relayer'].restarts>=self.max_relayer_restarts:self._err(errors,f'relayer:restart_exhausted:{terminal_rc}');break
                    self.states['relayer'].restarts+=1;self.states['relayer'].last_error=f'exit:{terminal_rc}';stop_event.wait(self.restart_delay_s)
                    if stop_event.is_set():break
                    proc,outq,reader=self._spawn();continue
                if item!='__NO_LINE__':
                    try:self.coordinator.ingest_line(item);self.states['relayer'].last_success_monotonic_ns=time.perf_counter_ns();self.states['relayer'].last_error=''
                    except Exception as exc:self._err(errors,'instrumentation:'+sanitize_text(exc))
                if self.periodic and time.monotonic()>=next_periodic:
                    try:self.periodic()
                    except Exception as exc:self._err(errors,'periodic:'+sanitize_text(exc))
                    next_periodic=time.monotonic()+self.periodic_interval_s
        finally:
            stop_event.set();self.states['relayer'].alive=False
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=10)
                except Exception:proc.kill();proc.wait()
            terminal_rc=proc.poll();reader.join(timeout=2)
            for t in threads:t.join(timeout=5)
        runtime=time.perf_counter_ns()-start;cycles=sum(s.cycles for k,s in self.states.items() if k.startswith('observer:'));restarts=self.states['relayer'].restarts
        return SupervisorResult('PASS' if not errors else 'PARTIAL',runtime,terminal_rc,cycles,restarts,errors)
