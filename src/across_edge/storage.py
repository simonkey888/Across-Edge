from __future__ import annotations
import json,sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from .model import DepositEvent,FillEvent,ShadowRecord

def _utc():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
class Store:
    def __init__(self,path:str|Path):
        self.db=sqlite3.connect(str(path),timeout=30);self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
CREATE TABLE IF NOT EXISTS deposits(deposit_key TEXT PRIMARY KEY,origin_chain_id INTEGER NOT NULL,destination_chain_id INTEGER NOT NULL,deposit_id TEXT NOT NULL,payload_json TEXT NOT NULL,block_number INTEGER NOT NULL,tx_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fills(tx_hash TEXT PRIMARY KEY,deposit_key TEXT NOT NULL,payload_json TEXT NOT NULL,block_number INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS shadow_records(run_id TEXT NOT NULL,deposit_key TEXT NOT NULL,schema_version INTEGER NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(run_id,deposit_key));
CREATE TABLE IF NOT EXISTS fills_v2(event_id TEXT PRIMARY KEY,tx_hash TEXT NOT NULL,log_index INTEGER NOT NULL,deposit_key TEXT NOT NULL,destination_chain_id INTEGER NOT NULL,payload_json TEXT NOT NULL,block_number INTEGER NOT NULL,block_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS fills_v2_deposit_order ON fills_v2(deposit_key,block_number,log_index,tx_hash,event_id);
CREATE TABLE IF NOT EXISTS shadow_records_v2(run_id TEXT NOT NULL,trace_id TEXT NOT NULL,deposit_key TEXT NOT NULL,schema_version INTEGER NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(run_id,trace_id));
CREATE INDEX IF NOT EXISTS shadow_records_v2_deposit ON shadow_records_v2(run_id,deposit_key);
CREATE TABLE IF NOT EXISTS candidate_transitions(run_id TEXT NOT NULL,trace_id TEXT NOT NULL,seq INTEGER NOT NULL,state TEXT NOT NULL,destination_time INTEGER NOT NULL,observed_wall_utc TEXT NOT NULL,source_chain_id INTEGER,source_block_number INTEGER,source_block_hash TEXT,PRIMARY KEY(run_id,trace_id,seq));
CREATE TABLE IF NOT EXISTS cursors(scope TEXT NOT NULL,chain_id INTEGER NOT NULL,next_block INTEGER NOT NULL,last_block_number INTEGER,last_block_hash TEXT,updated_utc TEXT NOT NULL,PRIMARY KEY(scope,chain_id));
CREATE TABLE IF NOT EXISTS run_cursors(run_id TEXT NOT NULL,scope TEXT NOT NULL,chain_id INTEGER NOT NULL,next_block INTEGER,last_block_number INTEGER,last_block_hash TEXT,updated_utc TEXT NOT NULL,PRIMARY KEY(run_id,scope,chain_id));
CREATE TABLE IF NOT EXISTS run_metadata(run_id TEXT PRIMARY KEY,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observer_counters(run_id TEXT NOT NULL,name TEXT NOT NULL,value INTEGER NOT NULL,PRIMARY KEY(run_id,name));
CREATE TABLE IF NOT EXISTS run_deposits(run_id TEXT NOT NULL,deposit_key TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(run_id,deposit_key));
CREATE TABLE IF NOT EXISTS run_deposit_snapshots(run_id TEXT NOT NULL,deposit_key TEXT NOT NULL,version_id TEXT NOT NULL,payload_json TEXT NOT NULL,observed_utc TEXT NOT NULL,PRIMARY KEY(run_id,deposit_key,version_id));
CREATE INDEX IF NOT EXISTS run_deposit_snapshots_lookup ON run_deposit_snapshots(run_id,deposit_key,observed_utc);
CREATE TABLE IF NOT EXISTS run_fills(run_id TEXT NOT NULL,event_id TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(run_id,event_id));
CREATE TABLE IF NOT EXISTS run_fill_observations(run_id TEXT NOT NULL,event_id TEXT NOT NULL,payload_json TEXT NOT NULL,observed_utc TEXT NOT NULL,PRIMARY KEY(run_id,event_id));
CREATE TABLE IF NOT EXISTS evaluation_attempts(run_id TEXT NOT NULL,evaluation_attempt_id TEXT NOT NULL,upstream_trace_id TEXT NOT NULL,deposit_key TEXT NOT NULL,deposit_version_id TEXT NOT NULL,created_monotonic_ns INTEGER NOT NULL,created_wall_utc TEXT NOT NULL,immutable_payload_json TEXT NOT NULL,PRIMARY KEY(run_id,evaluation_attempt_id));
CREATE INDEX IF NOT EXISTS evaluation_attempts_trace ON evaluation_attempts(run_id,upstream_trace_id,created_monotonic_ns);
CREATE TABLE IF NOT EXISTS active_attempts(run_id TEXT NOT NULL,upstream_trace_id TEXT NOT NULL,evaluation_attempt_id TEXT NOT NULL,PRIMARY KEY(run_id,upstream_trace_id));
CREATE TABLE IF NOT EXISTS evaluation_attempt_events(run_id TEXT NOT NULL,evaluation_attempt_id TEXT NOT NULL,stage TEXT NOT NULL,received_monotonic_ns INTEGER NOT NULL,wall_utc TEXT NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(run_id,evaluation_attempt_id,stage));
CREATE TABLE IF NOT EXISTS deposit_versions(run_id TEXT NOT NULL,deposit_key TEXT NOT NULL,version_id TEXT NOT NULL,fingerprint TEXT NOT NULL,provenance TEXT NOT NULL,fields_json TEXT NOT NULL,first_seen_utc TEXT NOT NULL,PRIMARY KEY(run_id,deposit_key,version_id));
CREATE TABLE IF NOT EXISTS deposit_aggregates(run_id TEXT NOT NULL,deposit_key TEXT NOT NULL,first_actionable_attempt_id TEXT,first_ready_attempt_id TEXT,current_decision_attempt_id TEXT,PRIMARY KEY(run_id,deposit_key));
CREATE TABLE IF NOT EXISTS decode_gaps(run_id TEXT NOT NULL,chain_id INTEGER NOT NULL,event_id TEXT NOT NULL,block_number INTEGER NOT NULL,block_hash TEXT,tx_hash TEXT,log_index INTEGER,topic0 TEXT,error_class TEXT,retry_count INTEGER NOT NULL DEFAULT 1,resolved INTEGER NOT NULL DEFAULT 0,first_seen_utc TEXT NOT NULL,last_seen_utc TEXT NOT NULL,PRIMARY KEY(run_id,chain_id,event_id));
''');self._migrate();self.db.commit()
    def _migrate(self):
        cols={r['name'] for r in self.db.execute('PRAGMA table_info(candidate_transitions)')}
        for name,typ in [('source_chain_id','INTEGER'),('source_block_number','INTEGER'),('source_block_hash','TEXT')]:
            if name not in cols:self.db.execute(f'ALTER TABLE candidate_transitions ADD COLUMN {name} {typ}')
    def close(self):self.db.close()
    @contextmanager
    def transaction(self):
        try:self.db.execute('BEGIN IMMEDIATE');yield;self.db.commit()
        except Exception:self.db.rollback();raise
    def upsert_deposit(self,e:DepositEvent,*,commit=True):self.db.execute('INSERT OR IGNORE INTO deposits VALUES(?,?,?,?,?,?,?)',(e.key,e.origin_chain_id,e.destination_chain_id,str(e.deposit_id),json.dumps(e.__dict__,sort_keys=True),e.block_number,e.tx_hash));self.db.commit() if commit else None
    def link_deposit(self,run_id,key,active=True,*,version_id=None,payload=None):
        self.db.execute('INSERT INTO run_deposits VALUES(?,?,?) ON CONFLICT(run_id,deposit_key) DO UPDATE SET active=excluded.active',(run_id,key,int(active)))
        if active and payload is not None and version_id is not None:self.db.execute('INSERT OR IGNORE INTO run_deposit_snapshots VALUES(?,?,?,?,?)',(run_id,key,version_id,json.dumps(payload,sort_keys=True),_utc()))
        self.db.commit()
    def deposit(self,key:str)->dict|None:
        r=self.db.execute('SELECT payload_json FROM deposits WHERE deposit_key=?',(key,)).fetchone();return json.loads(r[0]) if r else None
    def deposit_for_run(self,run_id:str,key:str)->dict|None:
        r=self.db.execute('SELECT payload_json FROM run_deposit_snapshots WHERE run_id=? AND deposit_key=? ORDER BY observed_utc DESC,version_id DESC LIMIT 1',(run_id,key)).fetchone();return json.loads(r[0]) if r else self.deposit(key)
    def insert_fill(self,e:FillEvent,*,commit=True)->bool:
        canonical=dict(e.__dict__);canonical['observed_monotonic_ns']=None;canonical['observed_wall_utc']=None;canonical['deposit_version_id']=None
        cur=self.db.execute('INSERT OR IGNORE INTO fills_v2 VALUES(?,?,?,?,?,?,?,?)',(e.event_id,e.tx_hash,e.log_index,e.key,e.destination_chain_id,json.dumps(canonical,sort_keys=True),e.block_number,e.block_hash))
        if cur.rowcount:self.db.execute('INSERT OR IGNORE INTO fills VALUES(?,?,?,?)',(e.tx_hash,e.key,json.dumps(canonical,sort_keys=True),e.block_number))
        if commit:self.db.commit()
        return cur.rowcount==1
    def link_fill(self,run_id,event_id,active=True,*,payload=None):
        prior=self.db.execute('SELECT active FROM run_fills WHERE run_id=? AND event_id=?',(run_id,event_id)).fetchone();was_active=bool(prior and prior['active'])
        self.db.execute('INSERT INTO run_fills VALUES(?,?,?) ON CONFLICT(run_id,event_id) DO UPDATE SET active=excluded.active',(run_id,event_id,int(active)))
        if active and payload is not None:
            packed=json.dumps(payload,sort_keys=True)
            if prior is None:self.db.execute('INSERT INTO run_fill_observations VALUES(?,?,?,?)',(run_id,event_id,packed,_utc()))
            elif not was_active:self.db.execute('INSERT OR REPLACE INTO run_fill_observations VALUES(?,?,?,?)',(run_id,event_id,packed,_utc()))
        self.db.commit()
    def fills_for_deposit(self,key:str,run_id:str|None=None)->list[dict]:
        if run_id is None:q='SELECT payload_json FROM fills_v2 WHERE deposit_key=? ORDER BY block_number,log_index,tx_hash,event_id';args=(key,)
        else:q='SELECT o.payload_json FROM run_fill_observations o JOIN run_fills rf ON rf.event_id=o.event_id AND rf.run_id=o.run_id AND rf.run_id=? AND rf.active=1 JOIN fills_v2 f ON f.event_id=o.event_id WHERE o.run_id=? AND f.deposit_key=? ORDER BY f.block_number,f.log_index,f.tx_hash,f.event_id';args=(run_id,run_id,key)
        return [json.loads(r[0]) for r in self.db.execute(q,args).fetchall()]
    def upsert_shadow(self,r:ShadowRecord,*,commit=True):
        if r.trace_id:self.db.execute('INSERT OR REPLACE INTO shadow_records_v2 VALUES(?,?,?,?,?)',(r.run_id,r.trace_id,r.deposit_key,r.schema_version,json.dumps(r.as_dict(),sort_keys=True)))
        else:self.db.execute('INSERT OR REPLACE INTO shadow_records VALUES(?,?,?,?)',(r.run_id,r.deposit_key,r.schema_version,json.dumps(r.as_dict(),sort_keys=True)))
        if commit:self.db.commit()
    def shadow_by_trace(self,run_id:str,trace_id:str)->dict|None:
        r=self.db.execute('SELECT payload_json FROM shadow_records_v2 WHERE run_id=? AND trace_id=?',(run_id,trace_id)).fetchone();return json.loads(r[0]) if r else None
    def shadow_rows(self,run_id:str)->list[dict]:
        rows=self.db.execute('SELECT s.payload_json FROM shadow_records_v2 s LEFT JOIN run_deposits rd ON rd.run_id=s.run_id AND rd.deposit_key=s.deposit_key WHERE s.run_id=? AND (rd.run_id IS NULL OR rd.active=1) ORDER BY s.deposit_key,s.trace_id',(run_id,)).fetchall()
        if not rows:rows=self.db.execute('SELECT payload_json FROM shadow_records WHERE run_id=? ORDER BY deposit_key',(run_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def shadow_for_deposit(self,run_id:str,key:str)->list[dict]:return [r for r in self.shadow_rows(run_id) if r['deposit_key']==key]
    def all_deposits(self,run_id:str|None=None)->list[dict]:
        if run_id is None:rows=self.db.execute('SELECT payload_json FROM deposits ORDER BY block_number,deposit_key').fetchall()
        else:rows=self.db.execute('SELECT s.payload_json FROM run_deposit_snapshots s JOIN run_deposits r ON r.deposit_key=s.deposit_key AND r.run_id=s.run_id WHERE s.run_id=? AND r.active=1 ORDER BY s.observed_utc,s.deposit_key,s.version_id',(run_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def all_fills(self,run_id:str|None=None)->list[dict]:
        if run_id is None:rows=self.db.execute('SELECT payload_json FROM fills_v2 ORDER BY block_number,log_index,tx_hash,event_id').fetchall()
        else:rows=self.db.execute('SELECT o.payload_json FROM run_fill_observations o JOIN run_fills r ON r.event_id=o.event_id AND r.run_id=o.run_id AND r.run_id=? AND r.active=1 JOIN fills_v2 f ON f.event_id=o.event_id WHERE o.run_id=? ORDER BY f.block_number,f.log_index,f.tx_hash,f.event_id',(run_id,run_id)).fetchall()
        if not rows and run_id is None:rows=self.db.execute('SELECT payload_json FROM fills ORDER BY block_number,tx_hash').fetchall()
        return [json.loads(r[0]) for r in rows]
    def add_transition(self,run_id:str,trace_id:str,state:str,destination_time:int,*,source_chain_id:int|None=None,source_block_number:int|None=None,source_block_hash:str|None=None,commit=True)->bool:
        prev=self.db.execute('SELECT state FROM candidate_transitions WHERE run_id=? AND trace_id=? ORDER BY seq DESC LIMIT 1',(run_id,trace_id)).fetchone()
        if prev and prev['state']==state:return False
        seq=self.db.execute('SELECT COALESCE(MAX(seq),-1)+1 FROM candidate_transitions WHERE run_id=? AND trace_id=?',(run_id,trace_id)).fetchone()[0];self.db.execute('INSERT INTO candidate_transitions(run_id,trace_id,seq,state,destination_time,observed_wall_utc,source_chain_id,source_block_number,source_block_hash) VALUES(?,?,?,?,?,?,?,?,?)',(run_id,trace_id,seq,state,destination_time,_utc(),source_chain_id,source_block_number,source_block_hash));self.db.commit() if commit else None;return True
    def transitions(self,run_id,trace_id):return [dict(r) for r in self.db.execute('SELECT * FROM candidate_transitions WHERE run_id=? AND trace_id=? ORDER BY seq',(run_id,trace_id))]
    def get_cursor(self,scope,chain_id,run_id=None):
        r=self.db.execute('SELECT * FROM run_cursors WHERE run_id=? AND scope=? AND chain_id=?',(run_id,scope,chain_id)).fetchone() if run_id is not None else self.db.execute('SELECT * FROM cursors WHERE scope=? AND chain_id=?',(scope,chain_id)).fetchone();return dict(r) if r else None
    def set_cursor(self,scope,chain_id,next_block,last_block_number,last_block_hash,*,run_id=None,commit=True):
        self.db.execute('INSERT OR REPLACE INTO run_cursors VALUES(?,?,?,?,?,?,?)',(run_id,scope,chain_id,next_block,last_block_number,last_block_hash,_utc())) if run_id is not None else self.db.execute('INSERT OR REPLACE INTO cursors VALUES(?,?,?,?,?,?)',(scope,chain_id,next_block,last_block_number,last_block_hash,_utc()));self.db.commit() if commit else None
    def create_version(self,run_id,key,version_id,fingerprint,provenance,fields):self.db.execute('INSERT OR IGNORE INTO deposit_versions VALUES(?,?,?,?,?,?,?)',(run_id,key,version_id,fingerprint,provenance,json.dumps(fields,sort_keys=True),_utc()));self.db.commit()
    def create_attempt(self,run_id,attempt_id,upstream_trace_id,key,version_id,created_ns,payload):self.db.execute('INSERT INTO evaluation_attempts VALUES(?,?,?,?,?,?,?,?)',(run_id,attempt_id,upstream_trace_id,key,version_id,created_ns,_utc(),json.dumps(payload,sort_keys=True)));self.db.execute('INSERT OR REPLACE INTO active_attempts VALUES(?,?,?)',(run_id,upstream_trace_id,attempt_id));self.db.commit()
    def active_attempt(self,run_id,upstream_trace_id):
        r=self.db.execute('SELECT evaluation_attempt_id FROM active_attempts WHERE run_id=? AND upstream_trace_id=?',(run_id,upstream_trace_id)).fetchone();return r[0] if r else None
    def record_attempt_stage(self,run_id,attempt_id,stage,received_ns,wall_utc,payload)->bool:
        cur=self.db.execute('INSERT OR IGNORE INTO evaluation_attempt_events VALUES(?,?,?,?,?,?)',(run_id,attempt_id,stage,received_ns,wall_utc,json.dumps(payload,sort_keys=True)));self.db.commit();return cur.rowcount==1
    def attempt_events(self,run_id,attempt_id):return [dict(r) for r in self.db.execute('SELECT stage,received_monotonic_ns,wall_utc,payload_json FROM evaluation_attempt_events WHERE run_id=? AND evaluation_attempt_id=? ORDER BY received_monotonic_ns',(run_id,attempt_id))]
    def set_aggregate(self,run_id,key,**updates):
        cur=self.db.execute('SELECT * FROM deposit_aggregates WHERE run_id=? AND deposit_key=?',(run_id,key)).fetchone();d=dict(cur) if cur else {'run_id':run_id,'deposit_key':key,'first_actionable_attempt_id':None,'first_ready_attempt_id':None,'current_decision_attempt_id':None};d.update({k:v for k,v in updates.items() if v is not None});self.db.execute('INSERT OR REPLACE INTO deposit_aggregates VALUES(?,?,?,?,?)',(d['run_id'],d['deposit_key'],d['first_actionable_attempt_id'],d['first_ready_attempt_id'],d['current_decision_attempt_id']));self.db.commit()
    def aggregate(self,run_id,key):
        r=self.db.execute('SELECT * FROM deposit_aggregates WHERE run_id=? AND deposit_key=?',(run_id,key)).fetchone();return dict(r) if r else None
    def record_decode_gap(self,run_id,chain_id,log,error):
        tx=str(log.get('transactionHash',''));idx=log.get('logIndex',-1);idx=int(idx,16) if isinstance(idx,str) else int(idx);bn=log.get('blockNumber',0);bn=int(bn,16) if isinstance(bn,str) else int(bn);eid=f'{tx.lower()}:{idx}';topic0=str((log.get('topics') or [''])[0]);now=_utc();err=type(error).__name__;self.db.execute('''INSERT INTO decode_gaps(run_id,chain_id,event_id,block_number,block_hash,tx_hash,log_index,topic0,error_class,retry_count,resolved,first_seen_utc,last_seen_utc) VALUES(?,?,?,?,?,?,?,?,?,1,0,?,?) ON CONFLICT(run_id,chain_id,event_id) DO UPDATE SET retry_count=retry_count+1,error_class=excluded.error_class,last_seen_utc=excluded.last_seen_utc,resolved=0''',(run_id,chain_id,eid,bn,str(log.get('blockHash','')),tx,idx,topic0,err,now,now));self.db.commit()
    def resolve_decode_gap(self,run_id,chain_id,event_id):self.db.execute('UPDATE decode_gaps SET resolved=1,last_seen_utc=? WHERE run_id=? AND chain_id=? AND event_id=?',(_utc(),run_id,chain_id,event_id));self.db.commit()
    def unresolved_decode_gaps(self,run_id):return [dict(r) for r in self.db.execute('SELECT * FROM decode_gaps WHERE run_id=? AND resolved=0 ORDER BY chain_id,block_number,log_index',(run_id,))]
    def counters(self,run_id):return {r['name']:r['value'] for r in self.db.execute('SELECT * FROM observer_counters WHERE run_id=?',(run_id,))}
    def bump_counter(self,run_id,name,delta=1):self.db.execute('INSERT INTO observer_counters VALUES(?,?,?) ON CONFLICT(run_id,name) DO UPDATE SET value=value+excluded.value',(run_id,name,delta));self.db.commit()
    def canonical_counters(self,run_id):
        deps=self.all_deposits(run_id);fills=self.all_fills(run_id);rows=self.shadow_rows(run_id);gaps=self.unresolved_decode_gaps(run_id);return {'deposits_observed':len(deps),'fills_observed':len(fills),'competitive_fills_observed':sum(int(f.get('fill_type',-1)) in {0,1} for f in fills),'slow_fills_observed':sum(int(f.get('fill_type',-1))==2 for f in fills),'unknown_fill_types':sum(int(f.get('fill_type',-1)) not in {0,1,2} for f in fills),'actionable_candidates':sum(r.get('ta_monotonic_ns') is not None and r.get('live_equivalent_confirmations_satisfied') is True for r in rows),'unresolved_decode_events':len(gaps)}
    def set_run_metadata(self,run_id,payload):self.db.execute('INSERT OR REPLACE INTO run_metadata VALUES(?,?)',(run_id,json.dumps(payload,sort_keys=True)));self.db.commit()
    def get_run_metadata(self,run_id):
        r=self.db.execute('SELECT payload_json FROM run_metadata WHERE run_id=?',(run_id,)).fetchone();return json.loads(r[0]) if r else None
    def _clear_run_deposit(self,run_id,key):
        traces=[r['trace_id'] for r in self.db.execute('SELECT trace_id FROM shadow_records_v2 WHERE run_id=? AND deposit_key=?',(run_id,key)).fetchall()]
        for trace in traces:self.db.execute('DELETE FROM candidate_transitions WHERE run_id=? AND trace_id=?',(run_id,trace));self.db.execute('DELETE FROM evaluation_attempt_events WHERE run_id=? AND evaluation_attempt_id=?',(run_id,trace));self.db.execute('DELETE FROM evaluation_attempts WHERE run_id=? AND evaluation_attempt_id=?',(run_id,trace));self.db.execute('DELETE FROM active_attempts WHERE run_id=? AND evaluation_attempt_id=?',(run_id,trace))
        self.db.execute('DELETE FROM shadow_records_v2 WHERE run_id=? AND deposit_key=?',(run_id,key));self.db.execute('DELETE FROM deposit_versions WHERE run_id=? AND deposit_key=?',(run_id,key));self.db.execute('DELETE FROM deposit_aggregates WHERE run_id=? AND deposit_key=?',(run_id,key));self.db.execute('DELETE FROM run_deposit_snapshots WHERE run_id=? AND deposit_key=?',(run_id,key))
    @staticmethod
    def _clear_winner_fields(d):
        for k,v in {'winner_relayer':'','winner_tx_hash':'','winner_block':None,'winner_log_index':None,'winner_fill_type':None,'winner_deposit_version_id':None,'tw_wall_utc':None,'tw_monotonic_ns':None,'winner_latency_ms':None,'shadow_headroom_ms':None}.items():d[k]=v
    @staticmethod
    def _apply_winner(d,winner):
        Store._clear_winner_fields(d)
        if winner:d.update(winner_relayer=winner['relayer'],winner_tx_hash=winner['tx_hash'],winner_block=winner['block_number'],winner_log_index=winner.get('log_index'),winner_fill_type=winner.get('fill_type'),winner_deposit_version_id=winner.get('deposit_version_id'),tw_wall_utc=winner.get('observed_wall_utc'),tw_monotonic_ns=winner.get('observed_monotonic_ns'))
    def rewind_chain(self,chain_id,from_block,run_id=None):
        with self.transaction():
            if run_id is None:
                doomed=[r['deposit_key'] for r in self.db.execute('SELECT deposit_key FROM deposits WHERE origin_chain_id=? AND block_number>=?',(chain_id,from_block)).fetchall()]
                affected_fill_keys=[r['deposit_key'] for r in self.db.execute('SELECT DISTINCT deposit_key FROM fills_v2 WHERE destination_chain_id=? AND block_number>=?',(chain_id,from_block)).fetchall()]
                self.db.execute('DELETE FROM deposits WHERE origin_chain_id=? AND block_number>=?',(chain_id,from_block));removed=[r['tx_hash'] for r in self.db.execute('SELECT tx_hash FROM fills_v2 WHERE destination_chain_id=? AND block_number>=?',(chain_id,from_block)).fetchall()];self.db.execute('DELETE FROM fills_v2 WHERE destination_chain_id=? AND block_number>=?',(chain_id,from_block))
                for tx in removed:self.db.execute('DELETE FROM fills WHERE tx_hash=?',(tx,))
                if doomed:
                    qs=','.join('?'*len(doomed));self.db.execute(f'DELETE FROM candidate_transitions WHERE trace_id IN (SELECT trace_id FROM shadow_records_v2 WHERE deposit_key IN ({qs}))',tuple(doomed));self.db.execute(f'DELETE FROM shadow_records_v2 WHERE deposit_key IN ({qs})',tuple(doomed))
                for key in sorted(set(affected_fill_keys)):
                    remaining=self.fills_for_deposit(key);winner=next((f for f in remaining if int(f.get('fill_type',-1)) in {0,1}),None)
                    for row in self.db.execute('SELECT run_id,trace_id,payload_json FROM shadow_records_v2 WHERE deposit_key=?',(key,)).fetchall():
                        d=json.loads(row['payload_json']);self._apply_winner(d,winner);self.db.execute('UPDATE shadow_records_v2 SET payload_json=? WHERE run_id=? AND trace_id=?',(json.dumps(d,sort_keys=True),row['run_id'],row['trace_id']))
                self.db.execute('DELETE FROM cursors WHERE chain_id=?',(chain_id,));return
            doomed=[r['deposit_key'] for r in self.db.execute('SELECT deposit_key FROM run_deposit_snapshots WHERE run_id=? AND json_extract(payload_json,\'$.origin_chain_id\')=? AND json_extract(payload_json,\'$.block_number\')>=?',(run_id,chain_id,from_block)).fetchall()]
            unique_doomed=sorted(set(doomed))
            if unique_doomed:
                qs=','.join('?'*len(unique_doomed));self.db.execute(f'UPDATE run_deposits SET active=0 WHERE run_id=? AND deposit_key IN ({qs})',(run_id,*unique_doomed))
            for key in unique_doomed:self._clear_run_deposit(run_id,key)
            self.db.execute('UPDATE run_fills SET active=0 WHERE run_id=? AND event_id IN (SELECT event_id FROM fills_v2 WHERE destination_chain_id=? AND block_number>=?)',(run_id,chain_id,from_block));self.db.execute('DELETE FROM candidate_transitions WHERE run_id=? AND source_chain_id=? AND source_block_number>=?',(run_id,chain_id,from_block));self.db.execute('DELETE FROM decode_gaps WHERE run_id=? AND chain_id=? AND block_number>=?',(run_id,chain_id,from_block));self.db.execute('DELETE FROM run_cursors WHERE run_id=? AND chain_id=?',(run_id,chain_id))
            for row in self.db.execute('SELECT trace_id,payload_json FROM shadow_records_v2 WHERE run_id=?',(run_id,)).fetchall():
                d=json.loads(row['payload_json']);hist=self.transitions(run_id,row['trace_id'])
                if d.get('destination_chain_id')==chain_id:
                    d['candidate_state_history']=hist
                    if hist:d['candidate_type']=hist[-1]['state'];d['decision_destination_time']=hist[-1]['destination_time']
                    else:d['candidate_type']='other';d['decision_destination_time']=None
                fills=self.fills_for_deposit(d['deposit_key'],run_id);winner=next((f for f in fills if int(f.get('fill_type',-1)) in {0,1}),None);self._apply_winner(d,winner)
                self.db.execute('UPDATE shadow_records_v2 SET payload_json=? WHERE run_id=? AND trace_id=?',(json.dumps(d,sort_keys=True),run_id,row['trace_id']))
    def get_attempt(self,run_id,attempt_id):
        r=self.db.execute('SELECT * FROM evaluation_attempts WHERE run_id=? AND evaluation_attempt_id=?',(run_id,attempt_id)).fetchone();return dict(r) if r else None
