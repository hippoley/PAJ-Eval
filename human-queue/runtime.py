"""Minimal durable HumanQueue runtime.

The runtime intentionally depends only on the Python standard library so the
core primitive can be embedded anywhere before a larger service is introduced.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


TERMINAL_STATES = {"approved", "rejected", "edited", "resolved"}


@dataclass(frozen=True)
class Wait:
    id: str
    uri: str
    title: str
    source: str
    state: str
    created_at: float
    decided_at: float | None
    decision: dict[str, Any] | None
    resume_token: str | None
    payload: dict[str, Any]


class HumanQueue:
    """A tiny durable human-boundary store backed by SQLite."""

    def __init__(self, db_path: str | Path = "human-queue.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS waits (
                    id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE,
                    uri TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    decided_at REAL,
                    decision_json TEXT,
                    resume_token TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def ask(
        self,
        *,
        uri: str,
        title: str,
        source: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        resume_token: str | None = None,
    ) -> Wait:
        """Create a durable wait or return the existing idempotent wait."""
        payload = payload or {}
        wait_id = f"wait_{uuid.uuid4().hex[:12]}"
        created_at = time.time()
        with self._connect() as conn:
            if idempotency_key:
                row = conn.execute(
                    "SELECT * FROM waits WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row:
                    return self._row_to_wait(row)

            conn.execute(
                """
                INSERT INTO waits (
                    id, idempotency_key, uri, title, source, state, created_at,
                    decided_at, decision_json, resume_token, payload_json
                ) VALUES (?, ?, ?, ?, ?, 'waiting', ?, NULL, NULL, ?, ?)
                """,
                (
                    wait_id,
                    idempotency_key,
                    uri,
                    title,
                    source,
                    created_at,
                    resume_token,
                    json.dumps(payload, sort_keys=True),
                ),
            )
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            assert row is not None
            return self._row_to_wait(row)

    def decide(
        self,
        wait_id: str,
        *,
        action: str,
        actor: str = "human",
        value: Any = None,
    ) -> Wait:
        """Resolve a wait exactly once.

        Replaying the same decision is idempotent. A conflicting second
        decision is rejected so two browser tabs cannot silently diverge.
        """
        now = time.time()
        decision = {"action": action, "actor": actor, "value": value}
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)

            current = self._row_to_wait(row)
            if current.state != "waiting":
                if current.decision == decision:
                    return current
                raise RuntimeError(f"{wait_id} already decided as {current.decision}")

            state = {
                "approve": "approved",
                "reject": "rejected",
                "edit": "edited",
            }.get(action, "resolved")
            conn.execute(
                """
                UPDATE waits
                   SET state = ?, decided_at = ?, decision_json = ?
                 WHERE id = ? AND state = 'waiting'
                """,
                (state, now, json.dumps(decision, sort_keys=True), wait_id),
            )
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            assert row is not None
            return self._row_to_wait(row)

    def get(self, wait_id: str) -> Wait:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)
            return self._row_to_wait(row)

    def pending(self) -> list[Wait]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM waits WHERE state = 'waiting' ORDER BY created_at"
            ).fetchall()
        return [self._row_to_wait(row) for row in rows]

    def wait_for_decision(
        self,
        wait_id: str,
        *,
        timeout: float | None = None,
        poll_interval: float = 0.1,
    ) -> Wait:
        """Block the caller until a human decision exists."""
        started = time.monotonic()
        while True:
            item = self.get(wait_id)
            if item.state in TERMINAL_STATES:
                return item
            if timeout is not None and time.monotonic() - started >= timeout:
                raise TimeoutError(wait_id)
            time.sleep(poll_interval)

    @staticmethod
    def _row_to_wait(row: sqlite3.Row) -> Wait:
        return Wait(
            id=row["id"],
            uri=row["uri"],
            title=row["title"],
            source=row["source"],
            state=row["state"],
            created_at=row["created_at"],
            decided_at=row["decided_at"],
            decision=json.loads(row["decision_json"]) if row["decision_json"] else None,
            resume_token=row["resume_token"],
            payload=json.loads(row["payload_json"]),
        )
