"""Revocable local sessions and one-use, browser-bound social sign-in transactions."""

import hashlib
import hmac
import re
import secrets
import time
from typing import Any

from app.store import LimitExceeded, Store

SESSION_TTL = 7 * 86400
FLOW_TTL = 600


class LoginError(Exception):
    pass


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Accounts:
    def __init__(self, store: Store, secret: str) -> None:
        self.store, self.secret = store, secret
        with store._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, provider TEXT NOT NULL, subject_hash TEXT NOT NULL,
                    name TEXT NOT NULL, created_at REAL NOT NULL, UNIQUE(provider,subject_hash)
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, owner TEXT NOT NULL, account_id TEXT,
                    expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_account ON sessions(account_id);
                CREATE TABLE IF NOT EXISTS login_flows (
                    state_hash TEXT PRIMARY KEY, binding_hash TEXT NOT NULL,
                    session_hash TEXT NOT NULL, provider TEXT NOT NULL,
                    verifier TEXT NOT NULL, nonce TEXT NOT NULL, expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_attempts (
                    client_key TEXT NOT NULL, action TEXT NOT NULL, at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS auth_attempts_client ON auth_attempts(client_key,at);
            """)

    def session(self, token: str) -> dict[str, Any] | None:
        if not re.fullmatch(r"[a-f0-9]{64}", token):
            return None
        with self.store._db() as db:
            row = db.execute(
                "SELECT s.*,a.name,a.provider FROM sessions s LEFT JOIN accounts a "
                "ON a.id = s.account_id WHERE token_hash = ? AND expires_at > ?",
                (digest(token), time.time()),
            ).fetchone()
            return dict(row) if row else None

    def guard(self, client_key: str, action: str) -> None:
        now = time.time()
        limit = 10 if action == "login" else 30
        with self.store._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM auth_attempts WHERE at <= ?", (now - 600,))
            row = db.execute(
                "SELECT count(*),min(at) FROM auth_attempts WHERE client_key = ? AND action = ?",
                (client_key, action),
            ).fetchone()
            if row[0] >= limit:
                raise LimitExceeded("auth_rate_limit", max(1, int(row[1] + 601 - now)))
            db.execute("INSERT INTO auth_attempts VALUES (?,?,?)", (client_key, action, now))

    def new_guest(self, client_key: str, owner: str | None = None) -> str:
        self.guard(client_key, "session")
        token = secrets.token_hex(32)
        with self.store._db() as db:
            db.execute(
                "INSERT INTO sessions VALUES (?,?,NULL,?)",
                (digest(token), owner or secrets.token_hex(16), time.time() + SESSION_TTL),
            )
        return token

    def begin(self, token: str, provider: str) -> tuple[str, str, str, str]:
        state, binding = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        verifier, nonce = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        with self.store._db() as db:
            db.execute(
                "DELETE FROM login_flows WHERE expires_at <= ? OR session_hash = ?",
                (time.time(), digest(token)),
            )
            db.execute(
                "INSERT INTO login_flows VALUES (?,?,?,?,?,?,?)",
                (
                    digest(state),
                    digest(binding),
                    digest(token),
                    provider,
                    verifier,
                    nonce,
                    time.time() + FLOW_TTL,
                ),
            )
        return state, binding, verifier, nonce

    def consume(self, provider: str, state: str, binding: str) -> dict[str, Any]:
        with self.store._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM login_flows WHERE state_hash = ?", (digest(state),)
            ).fetchone()
            if (
                not row
                or row["expires_at"] <= time.time()
                or row["provider"] != provider
                or not hmac.compare_digest(row["binding_hash"], digest(binding))
            ):
                raise LoginError("login_expired")
            db.execute("DELETE FROM login_flows WHERE state_hash = ?", (digest(state),))
            return dict(row)

    def finish(self, flow: dict[str, Any], subject: str, name: str) -> str:
        provider = flow["provider"]
        subject_hash = hmac.new(
            self.secret.encode(), f"{provider}:{subject}".encode(), hashlib.sha256
        ).hexdigest()
        token = secrets.token_hex(32)
        with self.store._db() as db:
            db.execute("BEGIN IMMEDIATE")
            session = db.execute(
                "SELECT * FROM sessions WHERE token_hash = ? AND expires_at > ?",
                (flow["session_hash"], time.time()),
            ).fetchone()
            if not session or session["account_id"]:
                raise LoginError("login_expired")
            row = db.execute(
                "SELECT id FROM accounts WHERE provider = ? AND subject_hash = ?",
                (provider, subject_hash),
            ).fetchone()
            # Stable pseudonymous identity also prevents deletion/re-registration resetting quota.
            account_id = row[0] if row else subject_hash[:32]
            if not row:
                db.execute(
                    "INSERT INTO accounts VALUES (?,?,?,?,?)",
                    (account_id, provider, subject_hash, name[:100], time.time()),
                )
            else:
                db.execute("UPDATE accounts SET name = ? WHERE id = ?", (name[:100], account_id))
            # Move guest ownership only after successful identity validation. Do not merge by email.
            db.execute("UPDATE jobs SET owner = ? WHERE owner = ?", (account_id, session["owner"]))
            db.execute(
                "UPDATE submissions SET request_key = NULL WHERE owner = ? AND request_key IN "
                "(SELECT request_key FROM submissions WHERE owner = ?)",
                (session["owner"], account_id),
            )
            db.execute(
                "UPDATE submissions SET owner = ? WHERE owner = ?", (account_id, session["owner"])
            )
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (flow["session_hash"],))
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?)",
                (digest(token), account_id, account_id, time.time() + SESSION_TTL),
            )
        return token

    def logout(self, token: str, all_devices: bool = False) -> None:
        with self.store._db() as db:
            session = db.execute(
                "SELECT account_id FROM sessions WHERE token_hash = ?", (digest(token),)
            ).fetchone()
            if session and session[0] and all_devices:
                db.execute("DELETE FROM sessions WHERE account_id = ?", (session[0],))
            else:
                db.execute("DELETE FROM sessions WHERE token_hash = ?", (digest(token),))
            db.execute("DELETE FROM login_flows WHERE session_hash = ?", (digest(token),))

    def delete(self, account_id: str) -> list[str]:
        with self.store._db() as db:
            db.execute("BEGIN IMMEDIATE")
            ids = [
                row[0] for row in db.execute("SELECT id FROM jobs WHERE owner = ?", (account_id,))
            ]
            db.execute(
                "DELETE FROM login_flows WHERE session_hash IN "
                "(SELECT token_hash FROM sessions WHERE account_id = ?)",
                (account_id,),
            )
            db.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))
            db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            # Expired rows retain only cleanup bookkeeping, never source history or titles.
            db.execute(
                "UPDATE jobs SET state = 'cancelled', expires_at = ?, url = '', title = '', "
                "error = NULL WHERE owner = ?",
                (time.time(), account_id),
            )
        return ids

    def prune(self) -> None:
        with self.store._db() as db:
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (time.time(),))
            db.execute("DELETE FROM login_flows WHERE expires_at <= ?", (time.time(),))
            db.execute("DELETE FROM auth_attempts WHERE at <= ?", (time.time() - 600,))
