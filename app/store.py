from __future__ import annotations

import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.config import Settings


class LimitExceeded(Exception):
    pass


class Store:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.data_dir / "jobs.sqlite3"
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, url TEXT NOT NULL,
                    kind TEXT NOT NULL, quality INTEGER NOT NULL, state TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '', progress REAL NOT NULL DEFAULT 0,
                    error TEXT, file_bytes INTEGER, created_at REAL NOT NULL,
                    updated_at REAL NOT NULL, expires_at REAL
                );
                CREATE INDEX IF NOT EXISTS jobs_owner ON jobs(owner, created_at);
                CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state, created_at);
                CREATE TABLE IF NOT EXISTS submissions (client_key TEXT NOT NULL, at REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS submissions_client ON submissions(client_key, at);
            """)

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(
        self, owner: str, client_key: str, url: str, kind: str, quality: int
    ) -> dict[str, Any]:
        now = time.time()
        job_id = uuid.uuid4().hex
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "DELETE FROM submissions WHERE at < ?", (now - self.settings.rate_window_seconds,)
            )
            count = db.execute(
                "SELECT count(*) FROM submissions WHERE client_key = ?", (client_key,)
            ).fetchone()[0]
            if count >= self.settings.rate_limit:
                raise LimitExceeded("rate_limit")
            active = "state IN ('queued','downloading','processing')"
            if (
                db.execute(f"SELECT count(*) FROM jobs WHERE {active}").fetchone()[0]
                >= self.settings.max_queue
            ):
                raise LimitExceeded("queue_full")
            own = db.execute(
                f"SELECT count(*) FROM jobs WHERE owner = ? AND {active}", (owner,)
            ).fetchone()[0]
            if own >= self.settings.max_active_per_session:
                raise LimitExceeded("session_limit")
            db.execute(
                "INSERT INTO jobs (id,owner,url,kind,quality,state,created_at,updated_at) "
                "VALUES (?,?,?,?,?,'queued',?,?)",
                (job_id, owner, url, kind, quality, now, now),
            )
            db.execute("INSERT INTO submissions VALUES (?,?)", (client_key, now))
            return dict(db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())

    def get(self, job_id: str, owner: str) -> dict[str, Any] | None:
        with self._db() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE id = ? AND owner = ? "
                "AND (expires_at IS NULL OR expires_at > ?)",
                (job_id, owner, time.time()),
            ).fetchone()
            return dict(row) if row else None

    def list_jobs(self, owner: str) -> list[dict[str, Any]]:
        with self._db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM jobs WHERE owner = ? AND (expires_at IS NULL OR expires_at > ?) "
                    "ORDER BY created_at DESC LIMIT 50",
                    (owner, time.time()),
                )
            ]

    def claim(self) -> dict[str, Any] | None:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM jobs WHERE state = 'queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE jobs SET state = 'downloading', updated_at = ? WHERE id = ?",
                (time.time(), row["id"]),
            )
            return {**dict(row), "state": "downloading"}

    def update(self, job_id: str, **fields: Any) -> None:
        allowed = {"state", "title", "progress", "error", "file_bytes"}
        if not fields or not fields.keys() <= allowed:
            raise ValueError("Invalid job update")
        fields["updated_at"] = time.time()
        if fields.get("state") in {"complete", "failed", "cancelled"}:
            fields["expires_at"] = time.time() + self.settings.retention_seconds
        assignments = ",".join(f"{name} = ?" for name in fields)
        with self._db() as db:
            db.execute(
                f"UPDATE jobs SET {assignments} WHERE id = ? "
                "AND state IN ('queued','downloading','processing')",
                (*fields.values(), job_id),
            )

    def recover(self) -> None:
        with self._db() as db:
            db.execute(
                "UPDATE jobs SET state = 'failed', error = 'interrupted', updated_at = ?, "
                "expires_at = ? WHERE state IN ('queued','downloading','processing')",
                (time.time(), time.time() + self.settings.retention_seconds),
            )

    def expire(self, now: float | None = None) -> list[str]:
        now = time.time() if now is None else now
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            ids = [
                row[0] for row in db.execute("SELECT id FROM jobs WHERE expires_at <= ?", (now,))
            ]
            db.execute("DELETE FROM jobs WHERE expires_at <= ?", (now,))
            db.execute(
                "DELETE FROM submissions WHERE at < ?", (now - self.settings.rate_window_seconds,)
            )
            return ids

    def retained_ids(self) -> set[str]:
        with self._db() as db:
            return {row[0] for row in db.execute("SELECT id FROM jobs WHERE state = 'complete'")}
