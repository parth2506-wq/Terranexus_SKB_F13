"""
CarbonKarma Part 2 — Persistent Memory Store (SQLite-backed, ChromaDB-compatible interface)
Full Store class with exact API signatures matching all Part 2 service callers.
"""
from __future__ import annotations
import hashlib, json, logging, math, os, sqlite3, time, uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "carbonkarma.db")

@contextmanager
def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    try:
        yield c; c.commit()
    except Exception:
        c.rollback(); raise
    finally:
        c.close()

def _init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, collection TEXT NOT NULL,
            content TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
            embedding TEXT NOT NULL DEFAULT '[]', created_at REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_coll ON documents(collection);
        CREATE INDEX IF NOT EXISTS idx_ct   ON documents(collection, created_at);

        CREATE TABLE IF NOT EXISTS wallets (
            farm_id TEXT PRIMARY KEY,
            balance REAL NOT NULL DEFAULT 0.0,
            updated_at REAL NOT NULL);

        CREATE TABLE IF NOT EXISTS wallet_transactions (
            tx_id TEXT PRIMARY KEY, farm_id TEXT NOT NULL,
            tx_type TEXT NOT NULL, amount REAL NOT NULL,
            reference TEXT DEFAULT '', data TEXT DEFAULT '{}',
            balance_after REAL NOT NULL DEFAULT 0.0,
            created_at REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_wtx ON wallet_transactions(farm_id);

        CREATE TABLE IF NOT EXISTS farm_profiles (
            farm_id TEXT PRIMARY KEY,
            profile TEXT NOT NULL,
            updated_at REAL NOT NULL);

        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY, farm_id TEXT NOT NULL,
            event_type TEXT NOT NULL, description TEXT DEFAULT '',
            data TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_ae ON audit_events(farm_id, created_at);
        """)
_init_db()

# ── Embedding helpers ─────────────────────────────────────────────────────
def _cosine(a, b):
    if not a or not b or len(a) != len(b): return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    return dot / (math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*x for x in b))+1e-9)

def _embed(doc: str, meta: Dict) -> List[float]:
    h = int(hashlib.md5(doc.encode()).hexdigest(), 16)
    base = [(h >> i) & 0xFF for i in range(0, 64, 4)]
    nums = [float(v) for v in meta.values() if isinstance(v, (int, float))]
    combined = (base + nums)[:32]
    norm = math.sqrt(sum(x*x for x in combined)) + 1e-9
    return [x/norm for x in combined]

# ── Collection (ChromaDB-compatible) ─────────────────────────────────────
class Collection:
    def __init__(self, name: str): self.name = name

    def add(self, ids, documents, metadatas=None, embeddings=None):
        now = time.time()
        metas = metadatas or [{} for _ in ids]
        with _conn() as c:
            for i, did in enumerate(ids):
                meta = metas[i] if i < len(metas) else {}
                doc  = documents[i] if i < len(documents) else ""
                emb  = embeddings[i] if embeddings and i < len(embeddings) else _embed(doc, meta)
                c.execute(
                    "INSERT OR REPLACE INTO documents(id,collection,content,metadata,embedding,created_at)"
                    " VALUES(?,?,?,?,?,?)",
                    (did, self.name, doc, json.dumps(meta), json.dumps(emb), now))

    def upsert(self, ids, documents, metadatas=None, embeddings=None):
        self.add(ids, documents, metadatas, embeddings)

    def query(self, query_texts=None, query_embeddings=None, n_results=5, where=None):
        with _conn() as c:
            rows = c.execute(
                "SELECT id,content,metadata,embedding FROM documents "
                "WHERE collection=? ORDER BY created_at DESC LIMIT 500", (self.name,)).fetchall()
        if where:
            rows = [r for r in rows
                    if all(json.loads(r["metadata"]).get(k)==v for k,v in where.items())]
        q = (_embed(query_texts[0], {}) if query_texts
             else (query_embeddings[0] if query_embeddings else None))
        scored = sorted(
            [(_cosine(q, json.loads(r["embedding"])) if q else 1.0, r) for r in rows],
            key=lambda x: -x[0])[:n_results]
        return {"ids": [[r["id"] for _,r in scored]],
                "documents": [[r["content"] for _,r in scored]],
                "metadatas": [[json.loads(r["metadata"]) for _,r in scored]],
                "distances": [[1-s for s,_ in scored]]}

    def get(self, ids=None, where=None):
        with _conn() as c:
            if ids:
                ph = ",".join("?"*len(ids))
                rows = c.execute(
                    f"SELECT id,content,metadata FROM documents "
                    f"WHERE collection=? AND id IN ({ph})",
                    [self.name]+list(ids)).fetchall()
            else:
                rows = c.execute(
                    "SELECT id,content,metadata FROM documents "
                    "WHERE collection=? ORDER BY created_at DESC", (self.name,)).fetchall()
        if where:
            rows = [r for r in rows
                    if all(json.loads(r["metadata"]).get(k)==v for k,v in where.items())]
        return {"ids": [r["id"] for r in rows],
                "documents": [r["content"] for r in rows],
                "metadatas": [json.loads(r["metadata"]) for r in rows]}

    def delete(self, ids=None, where=None):
        with _conn() as c:
            if ids:
                ph = ",".join("?"*len(ids))
                c.execute(
                    f"DELETE FROM documents WHERE collection=? AND id IN ({ph})",
                    [self.name]+list(ids))
            elif where:
                got = self.get(where=where)
                if got["ids"]: self.delete(ids=got["ids"])

    def count(self):
        with _conn() as c:
            return c.execute(
                "SELECT COUNT(*) FROM documents WHERE collection=?",
                (self.name,)).fetchone()[0]

# ── Store (high-level API matching all Part 2 service callers) ────────────
class Store:
    def __init__(self): self._cols: Dict[str, Collection] = {}

    def col(self, name: str) -> Collection:
        if name not in self._cols: self._cols[name] = Collection(name)
        return self._cols[name]

    # ── Observations / history ────────────────────────────────────────────
    def save_observation(self, farm_id: str, observation: Dict) -> str:
        oid = str(uuid.uuid4())
        ts  = observation.get("timestamp", "")
        self.col("field_history").upsert(
            ids=[oid], documents=[json.dumps(observation)],
            metadatas=[{"farm_id": farm_id, "timestamp": ts,
                        "water_level": float(observation.get("water_level", 0)),
                        "ndvi": float(observation.get("ndvi", 0))}])
        return oid

    def get_history(self, farm_id: str, limit: int = 100) -> List[Dict]:
        result = self.col("field_history").get(where={"farm_id": farm_id})
        docs = result.get("documents", [])
        out = []
        for d in docs[:limit]:
            try: out.append(json.loads(d))
            except: out.append({"raw": d})
        return out

    # ── Wallet (add_wallet_tx accepts both 'amount' and 'credits' kwargs) ─
    def add_wallet_tx(self, farm_id: str, tx_type: str,
                      amount: float = 0.0, credits: float = 0.0,
                      reference: str = "", data: Dict = None) -> Dict:
        """Issue or retire credits. Accepts either 'amount' or 'credits' kwarg."""
        delta = credits if credits != 0.0 else amount
        now   = time.time()
        tx_id = str(uuid.uuid4())
        with _conn() as c:
            c.execute(
                "INSERT INTO wallets(farm_id,balance,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(farm_id) DO UPDATE SET "
                "balance=balance+excluded.balance, updated_at=excluded.updated_at",
                (farm_id, delta, now))
            row = c.execute("SELECT balance FROM wallets WHERE farm_id=?",
                            (farm_id,)).fetchone()
            bal = float(row["balance"])
            c.execute(
                "INSERT INTO wallet_transactions"
                "(tx_id,farm_id,tx_type,amount,reference,data,balance_after,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (tx_id, farm_id, tx_type, delta, reference,
                 json.dumps(data or {}), bal, now))
        return {"tx_id": tx_id, "farm_id": farm_id, "tx_type": tx_type,
                "amount": delta, "reference": reference,
                "balance_after": bal, "created_at": now}

    def get_balance(self, farm_id: str) -> float:
        with _conn() as c:
            row = c.execute("SELECT balance FROM wallets WHERE farm_id=?",
                            (farm_id,)).fetchone()
        return float(row["balance"]) if row else 0.0

    def get_wallet_history(self, farm_id: str, limit: int = 50) -> List[Dict]:
        with _conn() as c:
            rows = c.execute(
                "SELECT tx_id,tx_type,amount,reference,data,balance_after,created_at "
                "FROM wallet_transactions WHERE farm_id=? ORDER BY created_at DESC LIMIT ?",
                (farm_id, limit)).fetchall()
        return [{"tx_id": r["tx_id"], "tx_type": r["tx_type"],
                 "amount": r["amount"], "reference": r["reference"],
                 "data": json.loads(r["data"]),
                 "balance_after": r["balance_after"],
                 "created_at": r["created_at"]} for r in rows]

    # ── Farm profile ──────────────────────────────────────────────────────
    def get_farm_profile(self, farm_id: str) -> Optional[Dict]:
        with _conn() as c:
            row = c.execute("SELECT profile FROM farm_profiles WHERE farm_id=?",
                            (farm_id,)).fetchone()
        return json.loads(row["profile"]) if row else None

    def upsert_farm_profile(self, farm_id: str, profile: Dict) -> None:
        with _conn() as c:
            c.execute(
                "INSERT INTO farm_profiles(farm_id,profile,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(farm_id) DO UPDATE SET "
                "profile=excluded.profile, updated_at=excluded.updated_at",
                (farm_id, json.dumps(profile), time.time()))

    # ── Audit events (accepts both 'data' and 'metadata' kwargs) ─────────
    def log_event(self, farm_id: str, event_type: str,
                  description: str = "", data: Dict = None, metadata: Dict = None) -> str:
        eid = str(uuid.uuid4())
        payload = data or metadata or {}
        with _conn() as c:
            c.execute(
                "INSERT INTO audit_events"
                "(event_id,farm_id,event_type,description,data,created_at)"
                " VALUES(?,?,?,?,?,?)",
                (eid, farm_id, event_type, description,
                 json.dumps(payload), time.time()))
        return eid

    def get_audit_trail(self, farm_id: str, limit: int = 50) -> List[Dict]:
        with _conn() as c:
            rows = c.execute(
                "SELECT event_id,event_type,description,data,created_at "
                "FROM audit_events WHERE farm_id=? "
                "ORDER BY created_at DESC LIMIT ?",
                (farm_id, limit)).fetchall()
        return [{"event_id": r["event_id"], "event_type": r["event_type"],
                 "description": r["description"],
                 "data": json.loads(r["data"]),
                 "created_at": r["created_at"]} for r in rows]

    # ── Reports ───────────────────────────────────────────────────────────
    def save_report(self, farm_id: str, report: Dict) -> str:
        rid = str(uuid.uuid4())
        self.col("reports").upsert(
            ids=[rid], documents=[json.dumps(report)],
            metadatas=[{"farm_id": farm_id,
                        "report_type": report.get("report_type", ""),
                        "created_at": str(time.time())}])
        return rid

    def get_reports(self, farm_id: str, limit: int = 10) -> List[Dict]:
        result = self.col("reports").get(where={"farm_id": farm_id})
        out = []
        for d in result.get("documents", [])[:limit]:
            try: out.append(json.loads(d))
            except: pass
        return out

    # ── Predictions ───────────────────────────────────────────────────────
    def save_prediction(self, farm_id: str, prediction: Dict) -> str:
        pid = str(uuid.uuid4())
        self.col("predictions").upsert(
            ids=[pid], documents=[json.dumps(prediction)],
            metadatas=[{"farm_id": farm_id, "created_at": str(time.time())}])
        return pid

    def insert_report(self, farm_id: str, report_type: str = "", summary: str = "",
                      data: Dict = None, pdf_path: str = "") -> str:
        """Alias for save_report - matches report_generator call signature."""
        report = {"farm_id": farm_id, "report_type": report_type,
                  "summary": summary, "data": data or {}, "pdf_path": pdf_path}
        return self.save_report(farm_id, report)

# ── Singleton ─────────────────────────────────────────────────────────────
_store: Optional[Store] = None
def get_store() -> Store:
    global _store
    if _store is None: _store = Store()
    return _store

def get_collection(name: str) -> Collection:
    return get_store().col(name)
