import json
import sqlite3
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS threads (
          thread_id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL, title TEXT NOT NULL,
          thread_type TEXT, author_id INTEGER, created_at TEXT, updated_at TEXT,
          raw_json TEXT NOT NULL, candidate_reason TEXT, extracted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, thread_id INTEGER NOT NULL REFERENCES threads(thread_id),
          importance TEXT NOT NULL, event_type TEXT, due_at TEXT, action_required TEXT,
          summary TEXT NOT NULL, raw_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
          course_id INTEGER PRIMARY KEY, code TEXT NOT NULL, name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS daily_digests (
          digest_date TEXT PRIMARY KEY, content TEXT NOT NULL,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

    def has_thread(self, thread_id: int) -> bool:
        return self.conn.execute("SELECT 1 FROM threads WHERE thread_id = ?", (thread_id,)).fetchone() is not None

    def add_thread(self, thread: dict[str, Any], reason: str | None) -> None:
        self.conn.execute("""INSERT OR IGNORE INTO threads
          (thread_id, course_id, title, thread_type, author_id, created_at, updated_at, raw_json, candidate_reason)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            int(thread["id"]), int(thread.get("course_id") or 0), thread.get("title", ""),
            thread.get("type", ""), thread.get("user_id"), thread.get("created_at", ""),
            thread.get("updated_at", ""), json.dumps(thread, ensure_ascii=False), reason,
        ))
        self.conn.commit()

    def upsert_course(self, course: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO courses (course_id, code, name) VALUES (?, ?, ?) "
            "ON CONFLICT(course_id) DO UPDATE SET code=excluded.code, name=excluded.name",
            (int(course["id"]), course.get("code", ""), course.get("name", "")),
        )
        self.conn.commit()

    def candidates(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM threads WHERE candidate_reason IS NOT NULL AND extracted_at IS NULL ORDER BY created_at").fetchall()

    def save_event(self, thread_id: int, event: dict[str, Any]) -> None:
        self.conn.execute("""INSERT INTO events (thread_id, importance, event_type, due_at, action_required, summary, raw_json)
          VALUES (?, ?, ?, ?, ?, ?, ?)""", (thread_id, event["importance"], event.get("event_type"), event.get("due_at"),
            event.get("action_required"), event["summary"], json.dumps(event, ensure_ascii=False)))
        self.conn.execute("UPDATE threads SET extracted_at = CURRENT_TIMESTAMP WHERE thread_id = ?", (thread_id,))
        self.conn.commit()

    def list_events(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT e.*, t.title FROM events e JOIN threads t USING(thread_id) ORDER BY e.created_at DESC").fetchall()

    def digest_events(self) -> list[sqlite3.Row]:
        return self.conn.execute("""
          SELECT e.*, t.title, t.course_id,
                 COALESCE(c.code, 'Course ' || t.course_id) AS course,
                 'https://edstem.org/us/courses/' || t.course_id || '/discussion/' || t.thread_id AS source_url
          FROM events e JOIN threads t USING(thread_id)
          LEFT JOIN courses c ON c.course_id = t.course_id
          WHERE e.importance IN ('high', 'medium')
          ORDER BY e.importance DESC, e.due_at, e.id DESC
        """).fetchall()

    def save_digest(self, digest_date: str, content: str) -> None:
        self.conn.execute(
            "INSERT INTO daily_digests (digest_date, content) VALUES (?, ?) "
            "ON CONFLICT(digest_date) DO UPDATE SET content=excluded.content, created_at=CURRENT_TIMESTAMP",
            (digest_date, content),
        )
        self.conn.commit()

    def get_digest(self, digest_date: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM daily_digests WHERE digest_date = ?", (digest_date,)).fetchone()
