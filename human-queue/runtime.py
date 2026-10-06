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
from typing import Any


TERMINAL_STATES = {"approved", "rejected", "edited", "resolved"}


@dataclass(frozen=True)
class AuditEvent:
    id: int
    wait_id: str
    event_type: str
    actor: str | None
    created_at: float
    data: dict[str, Any]


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
    claimed_by: str | None
    claim_expires_at: float | None
    execution_state: str | None
    resume_requested_at: float | None
    resumed_at: float | None
    completed_at: float | None
    resume_binding: dict[str, Any] | None


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
                    payload_json TEXT NOT NULL,
                    claimed_by TEXT,
                    claim_expires_at REAL,
                    execution_state TEXT,
                    resume_requested_at REAL,
                    resumed_at REAL,
                    completed_at REAL,
                    resume_binding_json TEXT
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(waits)").fetchall()
            }
            if "claimed_by" not in columns:
                conn.execute("ALTER TABLE waits ADD COLUMN claimed_by TEXT")
            if "claim_expires_at" not in columns:
                conn.execute("ALTER TABLE waits ADD COLUMN claim_expires_at REAL")
            if "execution_state" not in columns:
                conn.execute("ALTER TABLE waits ADD COLUMN execution_state TEXT")
            if "resume_requested_at" not in columns:
                conn.execute("ALTER TABLE waits ADD COLUMN resume_requested_at REAL")
            if "resumed_at" not in columns:
                conn.execute("ALTER TABLE waits ADD COLUMN resumed_at REAL")
            if "completed_at" not in columns:
                conn.execute("ALTER TABLE waits ADD COLUMN completed_at REAL")
            if "resume_binding_json" not in columns:
                conn.execute("ALTER TABLE waits ADD COLUMN resume_binding_json TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wait_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT,
                    created_at REAL NOT NULL,
                    data_json TEXT NOT NULL,
                    FOREIGN KEY(wait_id) REFERENCES waits(id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_wait_id "
                "ON audit_events(wait_id, id)"
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
        resume_binding: dict[str, Any] | None = None,
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

            try:
                conn.execute(
                    """
                    INSERT INTO waits (
                        id, idempotency_key, uri, title, source, state, created_at,
                        decided_at, decision_json, resume_token, payload_json,
                        resume_binding_json
                    ) VALUES (?, ?, ?, ?, ?, 'waiting', ?, NULL, NULL, ?, ?, ?)
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
                        json.dumps(resume_binding, sort_keys=True) if resume_binding else None,
                    ),
                )
            except sqlite3.IntegrityError:
                # A concurrent producer may have won the same idempotency key
                # after our initial read. Resolve that race into the existing
                # durable wait instead of surfacing a database error.
                conn.rollback()
                if not idempotency_key:
                    raise
                row = conn.execute(
                    "SELECT * FROM waits WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if row is None:
                    raise
                return self._row_to_wait(row)

            self._append_event(
                conn,
                wait_id,
                "WAIT_CREATED",
                actor=source,
                data={
                    "uri": uri,
                    "title": title,
                    "resume_token": resume_token,
                    "payload": payload,
                    "resume_binding": resume_binding,
                },
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
                   SET state = ?, decided_at = ?, decision_json = ?,
                       claimed_by = NULL, claim_expires_at = NULL
                 WHERE id = ? AND state = 'waiting'
                """,
                (state, now, json.dumps(decision, sort_keys=True), wait_id),
            )
            self._append_event(
                conn,
                wait_id,
                "DECISION_COMMITTED",
                actor=actor,
                data={"action": action, "value": value, "state": state},
            )
            if state != "rejected":
                conn.execute(
                    """
                    UPDATE waits
                       SET execution_state = 'resume_requested',
                           resume_requested_at = ?
                     WHERE id = ?
                    """,
                    (now, wait_id),
                )
                self._append_event(
                    conn,
                    wait_id,
                    "RESUME_REQUESTED",
                    actor=actor,
                    data={"resume_token": current.resume_token},
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

    def resume_requested(self) -> list[Wait]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM waits
                 WHERE execution_state = 'resume_requested'
                   AND resume_binding_json IS NOT NULL
                 ORDER BY resume_requested_at, created_at
                """
            ).fetchall()
        return [self._row_to_wait(row) for row in rows]

    def claim(
        self,
        wait_id: str,
        *,
        actor: str,
        lease_seconds: float = 30.0,
    ) -> Wait:
        """Claim a waiting item for a bounded lease.

        The same actor may renew its lease. Another actor may only claim after
        expiry. Decisions remain exactly-once independently of the lease.
        """
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        now = time.time()
        expires = now + lease_seconds
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            if item.state != "waiting":
                raise RuntimeError(f"{wait_id} is already {item.state}")
            if (
                item.claimed_by
                and item.claimed_by != actor
                and item.claim_expires_at
                and item.claim_expires_at > now
            ):
                raise RuntimeError(
                    f"{wait_id} is claimed by {item.claimed_by} "
                    f"until {item.claim_expires_at}"
                )
            previous_actor = item.claimed_by
            previous_expiry = item.claim_expires_at
            conn.execute(
                """
                UPDATE waits
                   SET claimed_by = ?, claim_expires_at = ?
                 WHERE id = ? AND state = 'waiting'
                """,
                (actor, expires, wait_id),
            )
            event_type = (
                "CLAIM_RENEWED"
                if previous_actor == actor
                and previous_expiry is not None
                and previous_expiry > now
                else "CLAIMED"
            )
            self._append_event(
                conn,
                wait_id,
                event_type,
                actor=actor,
                data={
                    "lease_seconds": lease_seconds,
                    "claim_expires_at": expires,
                    "previous_actor": previous_actor,
                },
            )
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            assert row is not None
            return self._row_to_wait(row)

    def release_claim(self, wait_id: str, *, actor: str) -> Wait:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            if item.claimed_by and item.claimed_by != actor:
                raise RuntimeError(f"{wait_id} is claimed by {item.claimed_by}")
            conn.execute(
                "UPDATE waits SET claimed_by = NULL, claim_expires_at = NULL WHERE id = ?",
                (wait_id,),
            )
            self._append_event(
                conn,
                wait_id,
                "CLAIM_RELEASED",
                actor=actor,
                data={},
            )
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            assert row is not None
            return self._row_to_wait(row)

    def mark_resumed(self, wait_id: str, *, actor: str = "machine") -> Wait:
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            if item.state == "rejected":
                raise RuntimeError(f"{wait_id} was rejected and cannot resume")
            if item.execution_state in {"resumed", "completed", "failed"}:
                return item
            if item.execution_state != "resume_requested":
                raise RuntimeError(f"{wait_id} has no resume request")
            conn.execute(
                """
                UPDATE waits
                   SET execution_state = 'resumed', resumed_at = ?
                 WHERE id = ?
                """,
                (now, wait_id),
            )
            self._append_event(
                conn,
                wait_id,
                "PROCESS_RESUMED",
                actor=actor,
                data={"resume_token": item.resume_token},
            )
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            assert row is not None
            return self._row_to_wait(row)

    def mark_completed(
        self,
        wait_id: str,
        *,
        actor: str = "machine",
        success: bool = True,
        detail: str | None = None,
    ) -> Wait:
        now = time.time()
        target_state = "completed" if success else "failed"
        event_type = "PROCESS_COMPLETED" if success else "PROCESS_FAILED"
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            if item.execution_state == target_state:
                return item
            if item.execution_state in {"completed", "failed"}:
                raise RuntimeError(
                    f"{wait_id} already finished as {item.execution_state}"
                )
            if item.execution_state != "resumed":
                raise RuntimeError(f"{wait_id} has not resumed")
            conn.execute(
                """
                UPDATE waits
                   SET execution_state = ?, completed_at = ?
                 WHERE id = ?
                """,
                (target_state, now, wait_id),
            )
            self._append_event(
                conn,
                wait_id,
                event_type,
                actor=actor,
                data={"detail": detail},
            )
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            assert row is not None
            return self._row_to_wait(row)

    def record_machine_callback_denied(
        self,
        wait_id: str,
        *,
        actor: str,
        callback: str,
        reason: str,
        data: dict[str, Any] | None = None,
    ) -> Wait:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM waits WHERE id = ?",
                (wait_id,),
            ).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            self._append_event(
                conn,
                wait_id,
                "MACHINE_CALLBACK_DENIED",
                actor=actor,
                data={
                    "callback": callback,
                    "reason": reason,
                    **(data or {}),
                },
            )
            return item

    def record_decision_denied(
        self,
        wait_id: str,
        *,
        actor: str,
        reason: str,
        data: dict[str, Any] | None = None,
    ) -> Wait:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM waits WHERE id = ?",
                (wait_id,),
            ).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            self._append_event(
                conn,
                wait_id,
                "DECISION_DENIED",
                actor=actor,
                data={
                    "reason": reason,
                    **(data or {}),
                },
            )
            return item

    def mark_resume_delivery_queued(
        self,
        wait_id: str,
        *,
        actor: str = "runtime",
        adapter: str,
        target: str,
        delivery_id: str,
        destination: str | None = None,
        destination_revision: int | None = None,
        destination_changed_by: str | None = None,
        destination_change_reason: str | None = None,
    ) -> Wait:
        data = {
            "adapter": adapter,
            "target": target,
            "delivery_id": delivery_id,
            "destination": destination,
            "destination_revision": destination_revision,
            "destination_changed_by": destination_changed_by,
            "destination_change_reason": destination_change_reason,
        }
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            if item.execution_state not in {
                "resume_requested",
                "resumed",
                "completed",
                "failed",
            }:
                raise RuntimeError(f"{wait_id} has no resume request")
            existing = conn.execute(
                """
                SELECT 1 FROM audit_events
                 WHERE wait_id = ? AND event_type = 'RESUME_DELIVERY_QUEUED'
                   AND data_json = ?
                 LIMIT 1
                """,
                (wait_id, json.dumps(data, sort_keys=True)),
            ).fetchone()
            if existing is None:
                self._append_event(
                    conn,
                    wait_id,
                    "RESUME_DELIVERY_QUEUED",
                    actor=actor,
                    data=data,
                )
            return item

    def record_resume_delivery_event(
        self,
        wait_id: str,
        *,
        event_type: str,
        actor: str,
        adapter: str,
        target: str,
        attempt: int,
        error: str | None = None,
        next_delay: float | None = None,
    ) -> Wait:
        allowed = {
            "RESUME_DELIVERY_ATTEMPT",
            "RESUME_DELIVERY_FAILED",
            "RESUME_DEAD_LETTERED",
        }
        if event_type not in allowed:
            raise ValueError(f"unsupported delivery event: {event_type}")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            if item.execution_state not in {
                "resume_requested",
                "resumed",
                "completed",
                "failed",
            }:
                raise RuntimeError(f"{wait_id} has no resume request")
            self._append_event(
                conn,
                wait_id,
                event_type,
                actor=actor,
                data={
                    "adapter": adapter,
                    "target": target,
                    "attempt": attempt,
                    "error": error,
                    "next_delay": next_delay,
                },
            )
            return item

    def mark_resume_dispatched(
        self,
        wait_id: str,
        *,
        actor: str = "adapter",
        adapter: str,
        target: str,
    ) -> Wait:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if row is None:
                raise KeyError(wait_id)
            item = self._row_to_wait(row)
            if item.execution_state not in {
                "resume_requested",
                "resumed",
                "completed",
                "failed",
            }:
                raise RuntimeError(f"{wait_id} has no resume request")

            existing = conn.execute(
                """
                SELECT 1 FROM audit_events
                 WHERE wait_id = ? AND event_type = 'RESUME_DISPATCHED'
                   AND data_json = ?
                 LIMIT 1
                """,
                (
                    wait_id,
                    json.dumps(
                        {"adapter": adapter, "target": target},
                        sort_keys=True,
                    ),
                ),
            ).fetchone()
            if existing is None:
                self._append_event(
                    conn,
                    wait_id,
                    "RESUME_DISPATCHED",
                    actor=actor,
                    data={"adapter": adapter, "target": target},
                )
            row = conn.execute("SELECT * FROM waits WHERE id = ?", (wait_id,)).fetchone()
            assert row is not None
            return self._row_to_wait(row)

    def recent_audit_events(self, limit: int = 100) -> list[AuditEvent]:
        if limit <= 0:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_event(row) for row in reversed(rows)]

    def audit_events(self, wait_id: str) -> list[AuditEvent]:
        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM waits WHERE id = ?", (wait_id,)).fetchone()
            if exists is None:
                raise KeyError(wait_id)
            rows = conn.execute(
                "SELECT * FROM audit_events WHERE wait_id = ? ORDER BY id",
                (wait_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    @staticmethod
    def _append_event(
        conn: sqlite3.Connection,
        wait_id: str,
        event_type: str,
        *,
        actor: str | None,
        data: dict[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO audit_events (
                wait_id, event_type, actor, created_at, data_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                wait_id,
                event_type,
                actor,
                time.time(),
                json.dumps(data, sort_keys=True),
            ),
        )

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
    def _row_to_event(row: sqlite3.Row) -> AuditEvent:
        return AuditEvent(
            id=row["id"],
            wait_id=row["wait_id"],
            event_type=row["event_type"],
            actor=row["actor"],
            created_at=row["created_at"],
            data=json.loads(row["data_json"]),
        )

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
            claimed_by=row["claimed_by"],
            claim_expires_at=row["claim_expires_at"],
            execution_state=row["execution_state"],
            resume_requested_at=row["resume_requested_at"],
            resumed_at=row["resumed_at"],
            completed_at=row["completed_at"],
            resume_binding=(
                json.loads(row["resume_binding_json"])
                if row["resume_binding_json"]
                else None
            ),
        )
