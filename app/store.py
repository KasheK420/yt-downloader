from __future__ import annotations

import math
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from app.config import Settings
from app.policy import Policy, policy_for


class LimitExceeded(Exception):
    def __init__(self, code: str, retry_after: int = 1) -> None:
        super().__init__(code)
        self.retry_after = retry_after


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
            # Additive migration keeps existing anonymous sessions and queued media valid.
            for table, fields in {
                "jobs": {"max_duration_seconds": "INTEGER", "max_file_bytes": "INTEGER"},
                "submissions": {"owner": "TEXT", "request_key": "TEXT", "job_id": "TEXT"},
            }.items():
                existing = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                for column, sql_type in fields.items():
                    if column not in existing:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}")
            db.execute("CREATE INDEX IF NOT EXISTS submissions_owner ON submissions(owner,at)")
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS submissions_request "
                "ON submissions(owner,request_key) WHERE request_key IS NOT NULL"
            )

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _repeated(
        db: sqlite3.Connection, owner: str, key: str | None, url: str, kind: str, quality: int
    ) -> dict[str, Any] | None:
        if not key:
            return None
        previous = db.execute(
            "SELECT job_id FROM submissions WHERE owner = ? AND request_key = ?", (owner, key)
        ).fetchone()
        if not previous:
            return None
        job = db.execute("SELECT * FROM jobs WHERE id = ?", (previous[0],)).fetchone()
        if not job or (job["expires_at"] and job["expires_at"] <= time.time()):
            raise ValueError("request_expired")
        if (job["url"], job["kind"], job["quality"]) != (url, kind, quality):
            raise ValueError("idempotency_conflict")
        return dict(job)

    def repeated(
        self, owner: str, key: str, url: str, kind: str, quality: int
    ) -> dict[str, Any] | None:
        with self._db() as db:
            return self._repeated(db, owner, key, url, kind, quality)

    def create(
        self,
        owner: str,
        client_key: str,
        url: str,
        kind: str,
        quality: int,
        *,
        policy: Policy | None = None,
        request_key: str | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        job_id = uuid.uuid4().hex
        policy = policy or policy_for(self.settings, False)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            if previous := self._repeated(db, owner, request_key, url, kind, quality):
                return previous

            def check(column: str, key: str, limit: int, window: int, code: str) -> None:
                times = [
                    row[0]
                    for row in db.execute(
                        f"SELECT at FROM submissions WHERE {column} = ? AND at > ? ORDER BY at",
                        (key, now - window),
                    )
                ]
                if len(times) >= limit:
                    raise LimitExceeded(code, max(1, math.ceil(times[-limit] + window - now)))

            check(
                "client_key",
                client_key,
                self.settings.rate_limit,
                self.settings.rate_window_seconds,
                "rate_limit",
            )
            if self.settings.public_mode:
                check(
                    "owner" if policy.account else "client_key",
                    owner if policy.account else client_key,
                    policy.downloads,
                    policy.window_seconds,
                    "quota_exhausted",
                )
                check(
                    "client_key",
                    client_key,
                    self.settings.public_ip_daily_limit,
                    86400,
                    "ip_daily_limit",
                )
            active = "state IN ('queued','downloading','processing')"
            if (
                db.execute(f"SELECT count(*) FROM jobs WHERE {active}").fetchone()[0]
                >= self.settings.max_queue
            ):
                raise LimitExceeded("queue_full")
            own = db.execute(
                f"SELECT count(*) FROM jobs WHERE owner = ? AND {active}", (owner,)
            ).fetchone()[0]
            if own >= policy.max_active:
                raise LimitExceeded("session_limit")
            db.execute(
                "INSERT INTO jobs (id,owner,url,kind,quality,state,created_at,updated_at,"
                "max_duration_seconds,max_file_bytes) VALUES (?,?,?,?,?,'queued',?,?,?,?)",
                (
                    job_id,
                    owner,
                    url,
                    kind,
                    quality,
                    now,
                    now,
                    policy.max_duration_seconds,
                    policy.max_file_bytes,
                ),
            )
            db.execute(
                "INSERT INTO submissions (client_key,at,owner,request_key,job_id) "
                "VALUES (?,?,?,?,?)",
                (client_key, now, owner, request_key, job_id),
            )
            return dict(db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())

    def budget(self, owner: str, client_key: str, policy: Policy) -> dict[str, Any]:
        column = "owner" if policy.account and self.settings.public_mode else "client_key"
        key = owner if column == "owner" else client_key
        now = time.time()
        with self._db() as db:
            times = [
                row[0]
                for row in db.execute(
                    f"SELECT at FROM submissions WHERE {column} = ? AND at > ? ORDER BY at",
                    (key, now - policy.window_seconds),
                )
            ]
        return {
            "limit": policy.downloads,
            "remaining": max(0, policy.downloads - len(times)),
            "window_seconds": policy.window_seconds,
            "resets_at": times[max(0, len(times) - policy.downloads)] + policy.window_seconds
            if times
            else None,
        }

    def prune_counters(self) -> None:
        window = max(
            86400,
            self.settings.free_window_seconds,
            self.settings.guest_window_seconds,
            self.settings.rate_window_seconds,
        )
        with self._db() as db:
            db.execute("DELETE FROM submissions WHERE at <= ?", (time.time() - window,))

    def expire_queue(self) -> None:
        now = time.time()
        with self._db() as db:
            db.execute(
                "UPDATE jobs SET state = 'failed', error = 'queue_timeout', updated_at = ?, "
                "expires_at = ? WHERE state = 'queued' AND created_at <= ?",
                (
                    now,
                    now + self.settings.retention_seconds,
                    now - self.settings.max_queue_wait_seconds,
                ),
            )

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
                "SELECT * FROM jobs WHERE state = 'queued' AND created_at > ? "
                "ORDER BY created_at LIMIT 1",
                (time.time() - self.settings.max_queue_wait_seconds,),
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

    def remove(self, job_id: str) -> None:
        with self._db() as db:
            db.execute(
                "UPDATE jobs SET expires_at = ? WHERE id = ? "
                "AND state IN ('complete','failed','cancelled')",
                (time.time(), job_id),
            )

    def cleanup_ids(self, now: float | None = None) -> list[str]:
        now = time.time() if now is None else now
        with self._db() as db:
            return [
                row[0]
                for row in db.execute(
                    "SELECT id FROM jobs WHERE expires_at <= ? OR state IN ('failed','cancelled')",
                    (now,),
                )
            ]

    def purge(self, job_id: str, now: float | None = None) -> None:
        with self._db() as db:
            db.execute(
                "DELETE FROM jobs WHERE id = ? AND expires_at <= ?",
                (job_id, time.time() if now is None else now),
            )

    def retained_ids(self) -> set[str]:
        with self._db() as db:
            return {row[0] for row in db.execute("SELECT id FROM jobs")}
