from __future__ import annotations
import json,sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any,Iterator
from .models import sha256_json,utc_now
PHASES=("RECEIVE","VALIDATE","ACK","PREPARE_ISOLATED_TARGET","WORK","RESULT_READY","FINALIZE_RESULT")
class LifecycleStore:
    def __init__(self,path:Path):
        self.path=path; path.parent.mkdir(parents=True,exist_ok=True); self.db=sqlite3.connect(path); self.db.row_factory=sqlite3.Row; self.db.execute("PRAGMA journal_mode=WAL"); self.db.execute("PRAGMA synchronous=FULL"); self._init()
    def _init(self):
        self.db.executescript("""CREATE TABLE IF NOT EXISTS execution (execution_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,lease_id TEXT NOT NULL,scope_hash TEXT NOT NULL,source_sha TEXT NOT NULL,phase TEXT NOT NULL,started_at TEXT NOT NULL,updated_at TEXT NOT NULL,terminal_status TEXT); CREATE TABLE IF NOT EXISTS receipts (execution_id TEXT NOT NULL,receipt_key TEXT NOT NULL,kind TEXT NOT NULL,payload_json TEXT NOT NULL,payload_hash TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(execution_id,receipt_key)); CREATE TABLE IF NOT EXISTS external_reads (execution_id TEXT NOT NULL,read_key TEXT NOT NULL,request_hash TEXT NOT NULL,response_json TEXT NOT NULL,response_hash TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(execution_id,read_key)); CREATE TABLE IF NOT EXISTS artifacts (execution_id TEXT NOT NULL,artifact_name TEXT NOT NULL,artifact_hash TEXT NOT NULL,path TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(execution_id,artifact_name));"""); self.db.commit()
    @contextmanager
    def transaction(self)->Iterator[sqlite3.Connection]:
        try: self.db.execute("BEGIN IMMEDIATE"); yield self.db; self.db.commit()
        except Exception: self.db.rollback(); raise
    @staticmethod
    def execution_id(job_id,lease_id,scope_hash): return sha256_json({"job_id":job_id,"lease_id":lease_id,"scope_hash":scope_hash})
    def begin(self,*,job_id,lease_id,scope_hash,source_sha):
        eid=self.execution_id(job_id,lease_id,scope_hash); now=utc_now()
        with self.transaction() as db:
            row=db.execute("SELECT * FROM execution WHERE execution_id=?",(eid,)).fetchone()
            if row:
                if row["job_id"]!=job_id or row["lease_id"]!=lease_id or row["scope_hash"]!=scope_hash or row["source_sha"]!=source_sha: raise ValueError("durable_execution_identity_mismatch")
            else: db.execute("INSERT INTO execution VALUES (?,?,?,?,?,?,?,?,NULL)",(eid,job_id,lease_id,scope_hash,source_sha,"RECEIVE",now,now))
        return eid
    def phase(self,eid):
        row=self.db.execute("SELECT phase FROM execution WHERE execution_id=?",(eid,)).fetchone()
        if not row: raise KeyError("execution_missing")
        return str(row[0])
    def advance(self,eid,phase):
        if phase not in PHASES: raise ValueError("invalid_phase")
        if PHASES.index(phase)<PHASES.index(self.phase(eid)): return
        self.db.execute("UPDATE execution SET phase=?,updated_at=? WHERE execution_id=?",(phase,utc_now(),eid)); self.db.commit()
    def terminal(self,eid,status): self.db.execute("UPDATE execution SET phase='FINALIZE_RESULT',terminal_status=?,updated_at=? WHERE execution_id=?",(status,utc_now(),eid)); self.db.commit()
    def receipt(self,eid,key,kind,payload):
        encoded=json.dumps(payload,sort_keys=True,separators=(",",":")); digest=sha256_json(payload)
        with self.transaction() as db:
            existing=db.execute("SELECT payload_json,payload_hash FROM receipts WHERE execution_id=? AND receipt_key=?",(eid,key)).fetchone()
            if existing:
                if existing["payload_hash"]!=digest: raise ValueError("receipt_replay_payload_mismatch")
                return json.loads(existing["payload_json"])
            db.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?)",(eid,key,kind,encoded,digest,utc_now()))
        return payload
    def list_receipts(self,eid):
        rows=self.db.execute("SELECT receipt_key,kind,payload_json,payload_hash,created_at FROM receipts WHERE execution_id=? ORDER BY rowid",(eid,)).fetchall()
        return [{"receipt_key":r["receipt_key"],"kind":r["kind"],"payload":json.loads(r["payload_json"]),"payload_hash":r["payload_hash"],"created_at":r["created_at"]} for r in rows]
    def cached_read(self,eid,key,request):
        request_hash=sha256_json(request); row=self.db.execute("SELECT request_hash,response_json FROM external_reads WHERE execution_id=? AND read_key=?",(eid,key)).fetchone()
        if not row: return None
        if row["request_hash"]!=request_hash: raise ValueError("external_read_replay_request_mismatch")
        return json.loads(row["response_json"])
    def record_read(self,eid,key,request,response):
        rh=sha256_json(request); sh=sha256_json(response); encoded=json.dumps(response,sort_keys=True,separators=(",",":"))
        with self.transaction() as db:
            row=db.execute("SELECT request_hash,response_hash,response_json FROM external_reads WHERE execution_id=? AND read_key=?",(eid,key)).fetchone()
            if row:
                if row["request_hash"]!=rh or row["response_hash"]!=sh: raise ValueError("external_read_duplicate_mismatch")
                return json.loads(row["response_json"])
            db.execute("INSERT INTO external_reads VALUES (?,?,?,?,?,?)",(eid,key,rh,encoded,sh,utc_now()))
        return response
    def record_artifact(self,eid,name,path,digest):
        with self.transaction() as db:
            row=db.execute("SELECT artifact_hash,path FROM artifacts WHERE execution_id=? AND artifact_name=?",(eid,name)).fetchone()
            if row:
                if row["artifact_hash"]!=digest or row["path"]!=str(path): raise ValueError("artifact_identity_mismatch")
                return
            db.execute("INSERT INTO artifacts VALUES (?,?,?,?,?)",(eid,name,digest,str(path),utc_now()))
    def close(self): self.db.close()
