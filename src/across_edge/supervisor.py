from __future__ import annotations
import os,queue,signal,threading,time
from dataclasses import dataclass,field
from .safety import sanitize_text
@dataclass
class ComponentState:
    cycles:int=0
    restarts:int=0
    last_success_monotonic_ns:int|None=None
    last_error:str=''
    alive:bool=False
    last_exit_code:int|None=None
@dataclass
class SupervisorResult:
    status:str
    runtime_monotonic_ns:int
    relayer_returncode:int|None
    observer_cycles:int
    relayer_restarts:int
    errors:list[str]=field(default_factory=list)
class ContinuousSupervisor:
    def __init__(self,*,coordinator,observers,process_factory,observer_interval_s:float=2.0,restart_delay_s:float=1.0,max_relayer_restarts:int=1000000,periodic=None,periodic_interval_s:float=30.0):
        self.coordinator=coordinator;self.observers=list(observers);self.process_factory=process_factory;self.observer_interval_s=max(.01,observer_interval_s);self.restart_delay_s=max(.01,restart_delay_s);self.max_relayer_restarts=max(0,max_relayer_restarts);self.periodic=periodic;self.periodic_interval_s=max(.05,periodic_interval_s);self.states={f'observer:{i}':ComponentState() for i in range(len(self.observers))};self.states['relayer']=ComponentState()
    @staticmethod
    def _err(errors,msg):errors.append(msg);errors[:]=errors[-100:]
    def health(self):return {'ready':self.states['relayer'].alive and all(v.alive for k,v in self.states.items() if k.startswith('observer:')),'components':{k:vars(v).copy() for k,v in self.states.items()}}
    @staticmethod
    def _materialize_observer(observer_or_factory):
        return observer_or_factory() if callable(observer_or_factory) and not hasattr(observer_or_factory,'run_once') else observer_or_factory
    def _observer_worker(self,idx,observer_or_factory,stop_event,errors):
        state=self.states[f'observer:{idx}'];observer=None;failures=0
        try:
            observer=self._materialize_observer(observer_or_factory);state.alive=True
            while not stop_event.is_set():
                try:observer.run_once();state.cycles+=1;state.last_success_monotonic_ns=time.perf_counter_ns();state.last_error='';failures=0;stop_event.wait(self.observer_interval_s)
                except Exception as exc:state.last_error=sanitize_text(exc);self._err(errors,f'observer:{idx}:{state.last_error}');failures+=1;state.restarts+=1;stop_event.wait(min(30.0,self.observer_interval_s*(2**min(failures,6))))
        except Exception as exc:
            state.last_error=sanitize_text(exc);self._err(errors,f'observer:{idx}:startup:{state.last_error}')
        finally:
            state.alive=False
            if observer is not None:
                close=getattr(observer,'close',None)
                if callable(close):
                    try:close()
                    except Exception as exc:self._err(errors,f'observer:{idx}:close:{sanitize_text(exc)}')
    @staticmethod
    def _reader(proc,outq):
        try:
            if proc.stdout:
                for line in proc.stdout:outq.put(line.rstrip('\n'))
        finally:outq.put(None)
    @staticmethod
    def _process_group(proc):
        try:
            pgid=os.getpgid(proc.pid)
            return pgid if pgid==proc.pid and pgid!=os.getpgrp() else None
        except (ProcessLookupError,PermissionError,OSError):return None
    @staticmethod
    def _signal_process_tree(proc,pgid,sig):
        if pgid is not None:
            try:os.killpg(pgid,sig);return
            except ProcessLookupError:return
            except (PermissionError,OSError):pass
        if proc.poll() is None:
            try:proc.send_signal(sig)
            except ProcessLookupError:pass
    @classmethod
    def _terminate_process_tree(cls,proc,pgid,grace_s:float=10.0):
        cls._signal_process_tree(proc,pgid,signal.SIGTERM)
        deadline=time.monotonic()+grace_s
        while proc.poll() is None and time.monotonic()<deadline:time.sleep(.05)
        if proc.poll() is None:cls._signal_process_tree(proc,pgid,signal.SIGKILL)
        try:proc.wait(timeout=2)
        except Exception:pass
        if pgid is not None:
            try:os.killpg(pgid,signal.SIGKILL)
            except (ProcessLookupError,PermissionError,OSError):pass
    def _spawn(self):
        proc=self.process_factory();pgid=self._process_group(proc);self.states['relayer'].alive=True;outq=queue.Queue();reader=threading.Thread(target=self._reader,args=(proc,outq),daemon=True);reader.start();return proc,pgid,outq,reader
    def run(self,stop_event,*,max_runtime_s:float|None=None)->SupervisorResult:
        start=time.perf_counter_ns();errors=[];threads=[]
        for idx,obs in enumerate(self.observers):
            t=threading.Thread(target=self._observer_worker,args=(idx,obs,stop_event,errors),daemon=False,name=f'across-edge-observer-{idx}');t.start();threads.append(t)
        proc,pgid,outq,reader=self._spawn();next_periodic=time.monotonic()
        terminal_rc=None
        try:
            while not stop_event.is_set():
                if max_runtime_s is not None and (time.perf_counter_ns()-start)/1e9>=max_runtime_s:stop_event.set();break
                try:item=outq.get(timeout=.05)
                except queue.Empty:item='__NO_LINE__'
                if item is None or proc.poll() is not None:
                    terminal_rc=proc.poll();self.states['relayer'].alive=False;self.states['relayer'].last_exit_code=terminal_rc
                    self._terminate_process_tree(proc,pgid,grace_s=2.0)
                    if stop_event.is_set():break
                    if self.states['relayer'].restarts>=self.max_relayer_restarts:self._err(errors,f'relayer:restart_exhausted:{terminal_rc}');break
                    self.states['relayer'].restarts+=1;self.states['relayer'].last_error=f'exit:{terminal_rc}';stop_event.wait(min(30.0,self.restart_delay_s*(2**min(self.states['relayer'].restarts-1,5))))
                    if stop_event.is_set():break
                    proc,pgid,outq,reader=self._spawn();continue
                if item!='__NO_LINE__':
                    try:self.coordinator.ingest_line(item);self.states['relayer'].last_success_monotonic_ns=time.perf_counter_ns();self.states['relayer'].last_error=''
                    except Exception as exc:self._err(errors,'instrumentation:'+sanitize_text(exc))
                if self.periodic and time.monotonic()>=next_periodic:
                    try:self.periodic()
                    except Exception as exc:self._err(errors,'periodic:'+sanitize_text(exc))
                    next_periodic=time.monotonic()+self.periodic_interval_s
        finally:
            stop_event.set();self.states['relayer'].alive=False;self._terminate_process_tree(proc,pgid);terminal_rc=proc.poll();self.states['relayer'].last_exit_code=terminal_rc;reader.join(timeout=2)
            for t in threads:t.join()
        runtime=time.perf_counter_ns()-start;cycles=sum(s.cycles for k,s in self.states.items() if k.startswith('observer:'));restarts=self.states['relayer'].restarts
        return SupervisorResult('PASS' if not errors else 'PARTIAL',runtime,terminal_rc,cycles,restarts,errors)
