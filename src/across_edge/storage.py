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
CREATE TABLE IF NOT EXISTS run_metadata(run_id TEXT PRIMARY KEY,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observer_counters(run_id TEXT NOT NULL,name TEXT NOT NULL,value INTEGER NOT NULL,PRIMARY KEY(run_id,name));
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
    def upsert_deposit(self,e:DepositEvent,*,commit=True):
        self.db.execute('INSERT OR REPLACE INTO deposits VALUES(?,?,?,?,?,?,?)',(e.key,e.origin_chain_id,e.destination_chain_id,str(e.deposit_id),json.dumps(e.__dict__,sort_keys=True),e.block_number,e.tx_hash));self.db.commit() if commit else None
    def deposit(self,key:str)->dict|None:
        r=self.db.execute('SELECT payload_json FROM deposits WHERE deposit_key=?',(key,)).fetchone();return json.loads(r[0]) if r else None
    def insert_fill(self,e:FillEvent,*,commit=True)->bool:
        cur=self.db.execute('INSERT OR IGNORE INTO fills_v2 VALUES(?,?,?,?,?,?,?,?)',(e.event_id,e.tx_hash,e.log_index,e.key,e.destination_chain_id,json.dumps(e.__dict__,sort_keys=True),e.block_number,e.block_hash))
        if cur.rowcount:self.db.execute('INSERT OR IGNORE INTO fills VALUES(?,?,?,?)',(e.tx_hash,e.key,json.dumps(e.__dict__,sort_keys=True),e.block_number))
        if commit:self.db.commit()
        return cur.rowcount==1
    def fills_for_deposit(self,key:str)->list[dict]:return [json.loads(r[0]) for r in self.db.execute('SELECT payload_json FROM fills_v2 WHERE deposit_key=? ORDER BY block_number,log_index,tx_hash,event_id',(key,)).fetchall()]
    def upsert_shadow(self,r:ShadowRecord,*,commit=True):
        if r.trace_id:self.db.execute('INSERT OR REPLACE INTO shadow_records_v2 VALUES(?,?,?,?,?)',(r.run_id,r.trace_id,r.deposit_key,r.schema_version,json.dumps(r.as_dict(),sort_keys=True)))
        else:self.db.execute('INSERT OR REPLACE INTO shadow_records VALUES(?,?,?,?)',(r.run_id,r.deposit_key,r.schema_version,json.dumps(r.as_dict(),sort_keys=True)))
        if commit:self.db.commit()
    def shadow_by_trace(self,run_id:str,trace_id:str)->dict|None:
        r=self.db.execute('SELECT payload_json FROM shadow_records_v2 WHERE run_id=? AND trace_id=?',(run_id,trace_id)).fetchone();return json.loads(r[0]) if r else None
    def shadow_rows(self,run_id:str)->list[dict]:
        rows=self.db.execute('SELECT payload_json FROM shadow_records_v2 WHERE run_id=? ORDER BY deposit_key,trace_id',(run_id,)).fetchall()
        if not rows:rows=self.db.execute('SELECT payload_json FROM shadow_records WHERE run_id=? ORDER BY deposit_key',(run_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def shadow_for_deposit(self,run_id:str,key:str)->list[dict]:
        rows=self.db.execute('SELECT payload_json FROM shadow_records_v2 WHERE run_id=? AND deposit_key=? ORDER BY trace_id',(run_id,key)).fetchall()
        if rows:return [json.loads(r[0]) for r in rows]
        return [r for r in self.shadow_rows(run_id) if r['deposit_key']==key]
    def all_deposits(self)->list[dict]:return [json.loads(r[0]) for r in self.db.execute('SELECT payload_json FROM deposits ORDER BY block_number,deposit_key')]
    def all_fills(self)->list[dict]:
        rows=self.db.execute('SELECT payload_json FROM fills_v2 ORDER BY block_number,log_index,tx_hash,event_id').fetchall()
        if not rows:rows=self.db.execute('SELECT payload_json FROM fills ORDER BY block_number,tx_hash').fetchall()
        return [json.loads(r[0]) for r in rows]
    def add_transition(self,run_id:str,trace_id:str,state:str,destination_time:int,*,source_chain_id:int|None=None,source_block_number:int|None=None,source_block_hash:str|None=None,commit=True)->bool:
        prev=self.db.execute('SELECT state FROM candidate_transitions WHERE run_id=? AND trace_id=? ORDER BY seq DESC LIMIT 1',(run_id,trace_id)).fetchone()
        if prev and prev['state']==state:return False
        seq=self.db.execute('SELECT COALESCE(MAX(seq),-1)+1 FROM candidate_transitions WHERE run_id=? AND trace_id=?',(run_id,trace_id)).fetchone()[0]
        self.db.execute('INSERT INTO candidate_transitions(run_id,trace_id,seq,state,destination_time,observed_wall_utc,source_chain_id,source_block_number,source_block_hash) VALUES(?,?,?,?,?,?,?,?,?)',(run_id,trace_id,seq,state,destination_time,_utc(),source_chain_id,source_block_number,source_block_hash));self.db.commit() if commit else None;return True
    def transitions(self,run_id:str,trace_id:str)->list[dict]:return [dict(r) for r in self.db.execute('SELECT * FROM candidate_transitions WHERE run_id=? AND trace_id=? ORDER BY seq',(run_id,trace_id))]
    def get_cursor(self,scope:str,chain_id:int):
        r=self.db.execute('SELECT * FROM cursors WHERE scope=? AND chain_id=?',(scope,chain_id)).fetchone();return dict(r) if r else None
    def set_cursor(self,scope:str,chain_id:int,next_block:int,last_block_number:int|None,last_block_hash:str|None,*,commit=True):
        self.db.execute('INSERT OR REPLACE INTO cursors VALUES(?,?,?,?,?,?)',(scope,chain_id,next_block,last_block_number,last_block_hash,_utc()));self.db.commit() if commit else None
    def record_decode_gap(self,run_id:str,chain_id:int,log:dict,error:BaseException):
        tx=str(log.get('transactionHash',''));idx=log.get('logIndex',-1);idx=int(idx,16) if isinstance(idx,str) else int(idx);bn=log.get('blockNumber',0);bn=int(bn,16) if isinstance(bn,str) else int(bn);eid=f'{tx.lower()}:{idx}';topic0=str((log.get('topics') or [''])[0]);now=_utc();err=type(error).__name__
        self.db.execute('''INSERT INTO decode_gaps(run_id,chain_id,event_id,block_number,block_hash,tx_hash,log_index,topic0,error_class,retry_count,resolved,first_seen_utc,last_seen_utc) VALUES(?,?,?,?,?,?,?,?,?,1,0,?,?) ON CONFLICT(run_id,chain_id,event_id) DO UPDATE SET retry_count=retry_count+1,error_class=excluded.error_class,last_seen_utc=excluded.last_seen_utc,resolved=0''',(run_id,chain_id,eid,bn,str(log.get('blockHash','')),tx,idx,topic0,err,now,now));self.db.commit()
    def resolve_decode_gap(self,run_id:str,chain_id:int,event_id:str):self.db.execute('UPDATE decode_gaps SET resolved=1,last_seen_utc=? WHERE run_id=? AND chain_id=? AND event_id=?',(_utc(),run_id,chain_id,event_id));self.db.commit()
    def unresolved_decode_gaps(self,run_id:str)->list[dict]:return [dict(r) for r in self.db.execute('SELECT * FROM decode_gaps WHERE run_id=? AND resolved=0 ORDER BY chain_id,block_number,log_index',(run_id,))]
    def rewind_chain(self,chain_id:int,from_block:int):
        with self.transaction():
            doomed_rows=self.db.execute('SELECT deposit_key FROM deposits WHERE origin_chain_id=? AND block_number>=?',(chain_id,from_block)).fetchall();doomed={r['deposit_key'] for r in doomed_rows};doomed_traces=[]
            if doomed:
                qs=','.join('?'*len(doomed));doomed_traces=[r['trace_id'] for r in self.db.execute(f'SELECT trace_id FROM shadow_records_v2 WHERE deposit_key IN ({qs})',tuple(doomed)).fetchall()]
            self.db.execute('DELETE FROM deposits WHERE origin_chain_id=? AND block_number>=?',(chain_id,from_block));removed=[r['tx_hash'] for r in self.db.execute('SELECT tx_hash FROM fills_v2 WHERE destination_chain_id=? AND block_number>=?',(chain_id,from_block)).fetchall()];self.db.execute('DELETE FROM fills_v2 WHERE destination_chain_id=? AND block_number>=?',(chain_id,from_block))
            for tx in removed:self.db.execute('DELETE FROM fills WHERE tx_hash=?',(tx,))
            for trace in doomed_traces:self.db.execute('DELETE FROM candidate_transitions WHERE trace_id=?',(trace,));self.db.execute('DELETE FROM shadow_records_v2 WHERE trace_id=?',(trace,))
            self.db.execute('DELETE FROM candidate_transitions WHERE source_chain_id=? AND source_block_number>=?',(chain_id,from_block));self.db.execute('DELETE FROM decode_gaps WHERE chain_id=? AND block_number>=?',(chain_id,from_block));self.db.execute('DELETE FROM cursors WHERE chain_id=?',(chain_id,))
            for row in self.db.execute('SELECT run_id,trace_id,payload_json FROM shadow_records_v2').fetchall():
                d=json.loads(row['payload_json']);changed=False
                if d.get('destination_chain_id')==chain_id:
                    hist=self.transitions(row['run_id'],row['trace_id']);d['candidate_state_history']=hist
                    if hist:d['candidate_type']=hist[-1]['state'];d['decision_destination_time']=hist[-1]['destination_time']
                    else:d['candidate_type']='other';d['decision_destination_time']=None
                    changed=True
                if d.get('winner_block') is not None and d.get('destination_chain_id')==chain_id and d['winner_block']>=from_block:
                    for k,v in {'winner_relayer':'','winner_tx_hash':'','winner_block':None,'winner_log_index':None,'winner_fill_type':None,'tw_wall_utc':None,'tw_monotonic_ns':None,'winner_latency_ms':None,'shadow_headroom_ms':None}.items():d[k]=v
                    changed=True
                if changed:self.db.execute('UPDATE shadow_records_v2 SET payload_json=? WHERE run_id=? AND trace_id=?',(json.dumps(d,sort_keys=True),row['run_id'],row['trace_id']))
    def set_run_metadata(self,run_id:str,payload:dict):self.db.execute('INSERT OR REPLACE INTO run_metadata VALUES(?,?)',(run_id,json.dumps(payload,sort_keys=True)));self.db.commit()
    def get_run_metadata(self,run_id:str):
        r=self.db.execute('SELECT payload_json FROM run_metadata WHERE run_id=?',(run_id,)).fetchone();return json.loads(r[0]) if r else None
    def bump_counter(self,run_id:str,name:str,delta:int=1):self.db.execute('INSERT INTO observer_counters VALUES(?,?,?) ON CONFLICT(run_id,name) DO UPDATE SET value=value+excluded.value',(run_id,name,delta));self.db.commit()
    def counters(self,run_id:str)->dict:return {r['name']:r['value'] for r in self.db.execute('SELECT * FROM observer_counters WHERE run_id=?',(run_id,))}
