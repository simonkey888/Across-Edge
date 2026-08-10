from __future__ import annotations
import json,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from .model import DepositEvent,FillEvent,ShadowRecord

def _utc():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
class Store:
    def __init__(self,path:str|Path):
        self.db=sqlite3.connect(str(path));self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
CREATE TABLE IF NOT EXISTS deposits(deposit_key TEXT PRIMARY KEY,origin_chain_id INTEGER NOT NULL,destination_chain_id INTEGER NOT NULL,deposit_id TEXT NOT NULL,payload_json TEXT NOT NULL,block_number INTEGER NOT NULL,tx_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fills(tx_hash TEXT PRIMARY KEY,deposit_key TEXT NOT NULL,payload_json TEXT NOT NULL,block_number INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS shadow_records(run_id TEXT NOT NULL,deposit_key TEXT NOT NULL,schema_version INTEGER NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(run_id,deposit_key));
CREATE TABLE IF NOT EXISTS fills_v2(event_id TEXT PRIMARY KEY,tx_hash TEXT NOT NULL,log_index INTEGER NOT NULL,deposit_key TEXT NOT NULL,destination_chain_id INTEGER NOT NULL,payload_json TEXT NOT NULL,block_number INTEGER NOT NULL,block_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shadow_records_v2(run_id TEXT NOT NULL,trace_id TEXT NOT NULL,deposit_key TEXT NOT NULL,schema_version INTEGER NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(run_id,trace_id));
CREATE INDEX IF NOT EXISTS shadow_records_v2_deposit ON shadow_records_v2(run_id,deposit_key);
CREATE TABLE IF NOT EXISTS candidate_transitions(run_id TEXT NOT NULL,trace_id TEXT NOT NULL,seq INTEGER NOT NULL,state TEXT NOT NULL,destination_time INTEGER NOT NULL,observed_wall_utc TEXT NOT NULL,PRIMARY KEY(run_id,trace_id,seq));
CREATE TABLE IF NOT EXISTS cursors(scope TEXT NOT NULL,chain_id INTEGER NOT NULL,next_block INTEGER NOT NULL,last_block_number INTEGER,last_block_hash TEXT,updated_utc TEXT NOT NULL,PRIMARY KEY(scope,chain_id));
CREATE TABLE IF NOT EXISTS run_metadata(run_id TEXT PRIMARY KEY,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS observer_counters(run_id TEXT NOT NULL,name TEXT NOT NULL,value INTEGER NOT NULL,PRIMARY KEY(run_id,name));
''');self.db.commit()
    def close(self):self.db.close()
    def upsert_deposit(self,e:DepositEvent):
        self.db.execute('INSERT OR REPLACE INTO deposits VALUES(?,?,?,?,?,?,?)',(e.key,e.origin_chain_id,e.destination_chain_id,str(e.deposit_id),json.dumps(e.__dict__,sort_keys=True),e.block_number,e.tx_hash));self.db.commit()
    def insert_fill(self,e:FillEvent)->bool:
        cur=self.db.execute('INSERT OR IGNORE INTO fills_v2 VALUES(?,?,?,?,?,?,?,?)',(e.event_id,e.tx_hash,e.log_index,e.key,e.destination_chain_id,json.dumps(e.__dict__,sort_keys=True),e.block_number,e.block_hash));
        if cur.rowcount:self.db.execute('INSERT OR IGNORE INTO fills VALUES(?,?,?,?)',(e.tx_hash,e.key,json.dumps(e.__dict__,sort_keys=True),e.block_number))
        self.db.commit();return cur.rowcount==1
    def upsert_shadow(self,r:ShadowRecord):
        if r.trace_id:
            self.db.execute('INSERT OR REPLACE INTO shadow_records_v2 VALUES(?,?,?,?,?)',(r.run_id,r.trace_id,r.deposit_key,r.schema_version,json.dumps(r.as_dict(),sort_keys=True)))
        else:self.db.execute('INSERT OR REPLACE INTO shadow_records VALUES(?,?,?,?)',(r.run_id,r.deposit_key,r.schema_version,json.dumps(r.as_dict(),sort_keys=True)))
        self.db.commit()
    def shadow_rows(self,run_id:str)->list[dict]:
        rows=self.db.execute('SELECT payload_json FROM shadow_records_v2 WHERE run_id=? ORDER BY deposit_key,trace_id',(run_id,)).fetchall()
        if not rows:rows=self.db.execute('SELECT payload_json FROM shadow_records WHERE run_id=? ORDER BY deposit_key',(run_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def shadow_for_deposit(self,run_id:str,key:str)->list[dict]:return [r for r in self.shadow_rows(run_id) if r['deposit_key']==key]
    def all_deposits(self)->list[dict]:return [json.loads(r[0]) for r in self.db.execute('SELECT payload_json FROM deposits ORDER BY block_number,deposit_key')]
    def all_fills(self)->list[dict]:
        rows=self.db.execute('SELECT payload_json FROM fills_v2 ORDER BY block_number,log_index').fetchall()
        if not rows:rows=self.db.execute('SELECT payload_json FROM fills ORDER BY block_number,tx_hash').fetchall()
        return [json.loads(r[0]) for r in rows]
    def add_transition(self,run_id:str,trace_id:str,state:str,destination_time:int)->bool:
        prev=self.db.execute('SELECT state FROM candidate_transitions WHERE run_id=? AND trace_id=? ORDER BY seq DESC LIMIT 1',(run_id,trace_id)).fetchone()
        if prev and prev['state']==state:return False
        seq=self.db.execute('SELECT COALESCE(MAX(seq),-1)+1 FROM candidate_transitions WHERE run_id=? AND trace_id=?',(run_id,trace_id)).fetchone()[0]
        self.db.execute('INSERT INTO candidate_transitions VALUES(?,?,?,?,?,?)',(run_id,trace_id,seq,state,destination_time,_utc()));self.db.commit();return True
    def transitions(self,run_id:str,trace_id:str)->list[dict]:return [dict(r) for r in self.db.execute('SELECT * FROM candidate_transitions WHERE run_id=? AND trace_id=? ORDER BY seq',(run_id,trace_id))]
    def get_cursor(self,scope:str,chain_id:int):
        r=self.db.execute('SELECT * FROM cursors WHERE scope=? AND chain_id=?',(scope,chain_id)).fetchone();return dict(r) if r else None
    def set_cursor(self,scope:str,chain_id:int,next_block:int,last_block_number:int|None,last_block_hash:str|None):
        self.db.execute('INSERT OR REPLACE INTO cursors VALUES(?,?,?,?,?,?)',(scope,chain_id,next_block,last_block_number,last_block_hash,_utc()));self.db.commit()
    def rewind_chain(self,chain_id:int,from_block:int):
        doomed=[r['deposit_key'] for r in self.db.execute('SELECT deposit_key FROM deposits WHERE origin_chain_id=? AND block_number>=?',(chain_id,from_block))]
        self.db.execute('DELETE FROM deposits WHERE origin_chain_id=? AND block_number>=?',(chain_id,from_block));self.db.execute('DELETE FROM fills_v2 WHERE destination_chain_id=? AND block_number>=?',(chain_id,from_block))
        for legacy in self.db.execute('SELECT tx_hash,payload_json,block_number FROM fills WHERE block_number>=?',(from_block,)).fetchall():
            try:payload=json.loads(legacy['payload_json'])
            except Exception:continue
            if payload.get('destination_chain_id')==chain_id:self.db.execute('DELETE FROM fills WHERE tx_hash=?',(legacy['tx_hash'],))
        for row in self.db.execute('SELECT run_id,trace_id,payload_json FROM shadow_records_v2').fetchall():
            d=json.loads(row['payload_json']);changed=False
            if d.get('deposit_key') in doomed:self.db.execute('DELETE FROM shadow_records_v2 WHERE run_id=? AND trace_id=?',(row['run_id'],row['trace_id']));continue
            if d.get('winner_block') is not None and d.get('destination_chain_id')==chain_id and d['winner_block']>=from_block:
                for k,v in {'winner_relayer':'','winner_tx_hash':'','winner_block':None,'tw_wall_utc':None,'tw_monotonic_ns':None,'winner_latency_ms':None,'shadow_headroom_ms':None}.items():d[k]=v
                self.db.execute('UPDATE shadow_records_v2 SET payload_json=? WHERE run_id=? AND trace_id=?',(json.dumps(d,sort_keys=True),row['run_id'],row['trace_id']));changed=True
        self.db.commit()
    def set_run_metadata(self,run_id:str,payload:dict):self.db.execute('INSERT OR REPLACE INTO run_metadata VALUES(?,?)',(run_id,json.dumps(payload,sort_keys=True)));self.db.commit()
    def get_run_metadata(self,run_id:str):
        r=self.db.execute('SELECT payload_json FROM run_metadata WHERE run_id=?',(run_id,)).fetchone();return json.loads(r[0]) if r else None
    def bump_counter(self,run_id:str,name:str,delta:int=1):self.db.execute('INSERT INTO observer_counters VALUES(?,?,?) ON CONFLICT(run_id,name) DO UPDATE SET value=value+excluded.value',(run_id,name,delta));self.db.commit()
    def counters(self,run_id:str)->dict:return {r['name']:r['value'] for r in self.db.execute('SELECT * FROM observer_counters WHERE run_id=?',(run_id,))}
