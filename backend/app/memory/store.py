"""
SQLite-backed cross-meeting memory.

Stores meetings, tasks, transcript chunks with their embeddings (float32
blobs) and agent action proposals. Vector search is brute-force cosine
similarity in numpy, which is plenty for a personal/team-sized corpus and
keeps the project dependency-light (swap in pgvector behind this class if
you outgrow it).
"""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    meeting_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    trace_json TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    due_date TEXT,
    owner TEXT NOT NULL,
    data_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    text TEXT NOT NULL,
    dim INTEGER NOT NULL,
    embedding BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    meeting_id TEXT,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MemoryStore:
    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            import os

            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(SCHEMA)

    # -- meetings ------------------------------------------------------

    def save_meeting(
        self,
        *,
        title: str,
        meeting_date: str,
        summary: Dict[str, Any],
        trace: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        chunks: List[str],
        embeddings: List[List[float]],
        meeting_id: Optional[str] = None,
    ) -> str:
        meeting_id = meeting_id or str(uuid.uuid4())
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO meetings (id, title, meeting_date, created_at, summary_json, trace_json) VALUES (?,?,?,?,?,?)",
                (meeting_id, title, meeting_date, _now(), json.dumps(summary), json.dumps(trace)),
            )
            for t in tasks:
                self._conn.execute(
                    "INSERT INTO tasks (id, meeting_id, status, due_date, owner, data_json) VALUES (?,?,?,?,?,?)",
                    (t["id"], meeting_id, t["status"], t.get("dueDate"), t["owner"], json.dumps(t)),
                )
            for i, (text, emb) in enumerate(zip(chunks, embeddings)):
                vec = np.asarray(emb, dtype=np.float32)
                self._conn.execute(
                    "INSERT INTO chunks (meeting_id, idx, text, dim, embedding) VALUES (?,?,?,?,?)",
                    (meeting_id, i, text, int(vec.shape[0]), vec.tobytes()),
                )
        return meeting_id

    def list_meetings(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT m.id, m.title, m.meeting_date, m.created_at, "
                "(SELECT COUNT(*) FROM tasks t WHERE t.meeting_id = m.id) AS task_count "
                "FROM meetings m ORDER BY m.meeting_date DESC, m.created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_meeting(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "meetingDate": row["meeting_date"],
            "createdAt": row["created_at"],
            "summary": json.loads(row["summary_json"]),
            "trace": json.loads(row["trace_json"]),
            "tasks": self.list_tasks(meeting_id=meeting_id),
        }

    def delete_meeting(self, meeting_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        return cur.rowcount > 0

    # -- tasks ---------------------------------------------------------

    def list_tasks(self, *, meeting_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = (
            "SELECT t.status, t.data_json, t.meeting_id, m.title, m.meeting_date FROM tasks t "
            "JOIN meetings m ON m.id = t.meeting_id WHERE 1=1"
        )
        args: List[Any] = []
        if meeting_id:
            sql += " AND t.meeting_id = ?"
            args.append(meeting_id)
        if status:
            sql += " AND t.status = ?"
            args.append(status)
        sql += " ORDER BY m.meeting_date, t.rowid"
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        out = []
        for r in rows:
            data = json.loads(r["data_json"])
            data["status"] = r["status"]
            data["meetingId"] = r["meeting_id"]
            data["meetingTitle"] = r["title"]
            data["meetingDate"] = r["meeting_date"]
            out.append(data)
        return out

    def update_task_status(self, task_id: str, status: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        return cur.rowcount > 0

    # -- vector search -------------------------------------------------

    def search(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        q = np.asarray(query_embedding, dtype=np.float32)
        with self._lock:
            rows = self._conn.execute(
                "SELECT c.meeting_id, c.idx, c.text, c.embedding, m.title, m.meeting_date "
                "FROM chunks c JOIN meetings m ON m.id = c.meeting_id WHERE c.dim = ?",
                (int(q.shape[0]),),
            ).fetchall()
        if not rows:
            return []
        matrix = np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
        norms = np.linalg.norm(matrix, axis=1) * (np.linalg.norm(q) or 1.0)
        scores = (matrix @ q) / np.where(norms == 0, 1.0, norms)
        top = np.argsort(-scores)[:k]
        return [
            {
                "meetingId": rows[i]["meeting_id"],
                "meetingTitle": rows[i]["title"],
                "meetingDate": rows[i]["meeting_date"],
                "chunkIndex": rows[i]["idx"],
                "text": rows[i]["text"],
                "score": round(float(scores[i]), 4),
            }
            for i in top
        ]

    # -- agent actions -------------------------------------------------

    def create_action(self, *, kind: str, payload: Dict[str, Any], meeting_id: Optional[str]) -> Dict[str, Any]:
        action_id = str(uuid.uuid4())
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO actions (id, meeting_id, kind, status, payload_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (action_id, meeting_id, kind, "pending", json.dumps(payload), now, now),
            )
        return self.get_action(action_id)  # type: ignore[return-value]

    def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        return self._action_row(row) if row else None

    def list_actions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        sql, args = "SELECT * FROM actions", []
        if status:
            sql += " WHERE status = ?"
            args.append(status)
        sql += " ORDER BY created_at DESC, rowid DESC"
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [self._action_row(r) for r in rows]

    def update_action(self, action_id: str, *, status: str, result: Optional[Dict[str, Any]] = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE actions SET status = ?, result_json = ?, updated_at = ? WHERE id = ?",
                (status, json.dumps(result) if result is not None else None, _now(), action_id),
            )

    @staticmethod
    def _action_row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "meetingId": row["meeting_id"],
            "kind": row["kind"],
            "status": row["status"],
            "payload": json.loads(row["payload_json"]),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
