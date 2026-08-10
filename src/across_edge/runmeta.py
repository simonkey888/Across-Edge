from __future__ import annotations
import hashlib,json,subprocess
from datetime import datetime,timezone
from time import perf_counter_ns
from urllib.parse import urlsplit
from .safety import sanitize_endpoint

def utc_now():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def git_head(repo='.')->str:
    p=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],text=True,capture_output=True,check=False);return p.stdout.strip() if p.returncode==0 else 'UNKNOWN'
def config_fingerprint(config:dict)->str:
    safe={k:('<REDACTED>' if any(x in k.upper() for x in ('KEY','TOKEN','SECRET','PASSWORD','MNEMONIC')) else v) for k,v in config.items()};return hashlib.sha256(json.dumps(safe,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def endpoint_class(url:str)->str:
    p=urlsplit(sanitize_endpoint(url));return f'{p.scheme}://{p.hostname or "unknown"}'
class RunMetadata:
    def __init__(self,run_id:str,*,our_sha:str,upstream_sha:str,config:dict,routes:list[str],endpoints:list[str]):
        self.started_ns=perf_counter_ns();self.payload={'run_id':run_id,'schema_version':3,'our_sha':our_sha,'upstream_sha':upstream_sha,'start_utc':utc_now(),'end_utc':None,'runtime_monotonic_ns':None,'config_fingerprint_sha256':config_fingerprint(config),'routes':sorted(routes),'endpoint_classes':sorted({endpoint_class(e) for e in endpoints}),'tests':'UNKNOWN','safety':'UNKNOWN','secret_scan':'UNKNOWN','evidence_provenance':{},'known_unknowns':[]}
    def finish(self,**states):self.payload['end_utc']=utc_now();self.payload['runtime_monotonic_ns']=perf_counter_ns()-self.started_ns;self.payload.update(states);return self.payload
