from __future__ import annotations
import json, sqlite3
from pathlib import Path
from .model import DepositEvent, FillEvent, ShadowRecord
class Store:
    def __init__(self,path:str|Path):
        self.db=sqlite3.connect(str(path)); self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""CREATE TABLE IF NOT EXISTS deposits(deposit_key TEXT PRIMARY KEY,origin_chain_id INTEGER NOT NULL,destination_chain_id INTEGER NOT NULL,deposit_id TEXT NOT NULL,payload_json TEXT NOT NULL,block_number INTEGER NOT NULL,tx_hash TEXT NOT NULL);CREATE TABLE IF NOT EXISTS fills(tx_hash TEXT PRIMARY KEY,deposit_key TEXT NOT NULL,payload_json TEXT NOT NULL,block_number INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS shadow_records(run_id TEXT NOT NULL,deposit_key TEXT NOT NULL,schema_version INTEGER NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(run_id,deposit_key));"""); self.db.commit()
    def close(self): self.db.close()
    def upsert_deposit(self,e:DepositEvent):
        self.db.execute("INSERT OR REPLACE INTO deposits VALUES(?,?,?,?,?,?,?)",(e.key,e.origin_chain_id,e.destination_chain_id,str(e.deposit_id),json.dumps(e.__dict__,sort_keys=True),e.block_number,e.tx_hash)); self.db.commit()
    def insert_fill(self,e:FillEvent)->bool:
        cur=self.db.execute("INSERT OR IGNORE INTO fills VALUES(?,?,?,?)",(e.tx_hash,e.key,json.dumps(e.__dict__,sort_keys=True),e.block_number)); self.db.commit(); return cur.rowcount==1
    def upsert_shadow(self,r:ShadowRecord):
        self.db.execute("INSERT OR REPLACE INTO shadow_records VALUES(?,?,?,?)",(r.run_id,r.deposit_key,r.schema_version,json.dumps(r.as_dict(),sort_keys=True))); self.db.commit()
    def shadow_rows(self,run_id:str)->list[dict]: return [json.loads(r[0]) for r in self.db.execute("SELECT payload_json FROM shadow_records WHERE run_id=? ORDER BY deposit_key",(run_id,)).fetchall()]
    def all_deposits(self)->list[dict]: return [json.loads(r[0]) for r in self.db.execute("SELECT payload_json FROM deposits ORDER BY block_number")]
    def all_fills(self)->list[dict]: return [json.loads(r[0]) for r in self.db.execute("SELECT payload_json FROM fills ORDER BY block_number")]
