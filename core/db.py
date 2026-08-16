"""SQLite 历史: 核验/搜索/聊天记录持久化(评审: SQLite 从"工具"到"应用")"""
import json, os, sqlite3, threading

DATA_DIR = os.path.expanduser("~/.liodesktop")
DB_PATH = os.path.join(DATA_DIR, "liodesktop.db")
_lock = threading.Lock()

def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT NOT NULL,
        query TEXT,
        result TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    )""")
    return c

def db_add(kind, query, result):
    try:
        with _lock:
            c = _conn()
            c.execute("INSERT INTO history (kind, query, result) VALUES (?,?,?)",
                      (kind, query, result))
            c.commit(); c.close()
    except Exception:
        pass

def db_query(kind, limit=10):
    try:
        with _lock:
            c = _conn()
            rows = c.execute(
                "SELECT query, result, created_at FROM history WHERE kind=? "
                "ORDER BY id DESC LIMIT ?", (kind, limit)).fetchall()
            c.close()
        return [{"query": q, "result": r, "time": t} for q, r, t in rows]
    except Exception:
        return []
