"""Crash-safe resume delivery queue.

The queue persists delivery intent and scheduling metadata, never adapter
credentials. Workers register adapters at runtime and claim due jobs with a
bounded lease so another worker can take over after a crash.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from adapters import ResumeAdapter, RetryPolicy
from destinations import DestinationRegistry, resolve_resume_binding
from runtime import HumanQueue


@dataclass(frozen=True)
class Delivery:
    id: str
    wait_id: str
    adapter: str
    target: str
    destination: str | None
    destination_revision: int | None
    destination_changed_by: str | None
    destination_change_reason: str | None
    allowed_machine_actors: tuple[str, ...]
    status: str
    attempt: int
    max_attempts: int
    base_delay: float
    multiplier: float
    max_delay: float
    next_attempt_at: float
    claimed_by: str | None
    claim_expires_at: float | None
    last_error: str | None
    created_at: float
    updated_at: float


class DurableDeliveryQueue:
    def __init__(self, db_path: str | Path) -> None:
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
                CREATE TABLE IF NOT EXISTS resume_deliveries (
                    id TEXT PRIMARY KEY,
                    wait_id TEXT NOT NULL,
                    adapter TEXT NOT NULL,
                    target TEXT NOT NULL,
                    destination TEXT,
                    destination_revision INTEGER,
                    destination_changed_by TEXT,
                    destination_change_reason TEXT,
                    allowed_machine_actors_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    base_delay REAL NOT NULL,
                    multiplier REAL NOT NULL,
                    max_delay REAL NOT NULL,
                    next_attempt_at REAL NOT NULL,
                    claimed_by TEXT,
                    claim_expires_at REAL,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(wait_id, adapter, target)
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(resume_deliveries)"
                ).fetchall()
            }
            if "destination" not in columns:
                conn.execute(
                    "ALTER TABLE resume_deliveries ADD COLUMN destination TEXT"
                )
            if "destination_revision" not in columns:
                conn.execute(
                    "ALTER TABLE resume_deliveries "
                    "ADD COLUMN destination_revision INTEGER"
                )
            if "destination_changed_by" not in columns:
                conn.execute(
                    "ALTER TABLE resume_deliveries "
                    "ADD COLUMN destination_changed_by TEXT"
                )
            if "destination_change_reason" not in columns:
                conn.execute(
                    "ALTER TABLE resume_deliveries "
                    "ADD COLUMN destination_change_reason TEXT"
                )
            if "allowed_machine_actors_json" not in columns:
                conn.execute(
                    "ALTER TABLE resume_deliveries "
                    "ADD COLUMN allowed_machine_actors_json TEXT "
                    "NOT NULL DEFAULT '[]'"
                )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_resume_deliveries_due
                ON resume_deliveries(status, next_attempt_at, claim_expires_at)
                """
            )

    def enqueue(
        self,
        wait_id: str,
        *,
        adapter: str,
        target: str,
        policy: RetryPolicy | None = None,
        destination: str | None = None,
        destination_revision: int | None = None,
        destination_changed_by: str | None = None,
        destination_change_reason: str | None = None,
        allowed_machine_actors: list[str] | tuple[str, ...] | None = None,
        now: float | None = None,
    ) -> Delivery:
        policy = policy or RetryPolicy()
        if policy.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        now = time.time() if now is None else now
        delivery_id = f"delivery_{uuid.uuid4().hex[:12]}"
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO resume_deliveries (
                        id, wait_id, adapter, target, destination,
                        destination_revision, destination_changed_by,
                        destination_change_reason, allowed_machine_actors_json,
                        status, attempt,
                        max_attempts, base_delay, multiplier, max_delay,
                        next_attempt_at, claimed_by, claim_expires_at,
                        last_error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?, ?, ?,
                              NULL, NULL, NULL, ?, ?)
                    """,
                    (
                        delivery_id,
                        wait_id,
                        adapter,
                        target,
                        destination,
                        destination_revision,
                        destination_changed_by,
                        destination_change_reason,
                        json.dumps(sorted(set(allowed_machine_actors or ()))),
                        policy.max_attempts,
                        policy.base_delay,
                        policy.multiplier,
                        policy.max_delay,
                        now,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                row = conn.execute(
                    """
                    SELECT * FROM resume_deliveries
                     WHERE wait_id = ? AND adapter = ? AND target = ?
                    """,
                    (wait_id, adapter, target),
                ).fetchone()
                if row is None:
                    raise
                return self._row(row)
            row = conn.execute(
                "SELECT * FROM resume_deliveries WHERE id = ?",
                (delivery_id,),
            ).fetchone()
            assert row is not None
            return self._row(row)

    def get(self, delivery_id: str) -> Delivery:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM resume_deliveries WHERE id = ?",
                (delivery_id,),
            ).fetchone()
            if row is None:
                raise KeyError(delivery_id)
            return self._row(row)

    def for_wait(self, wait_id: str) -> Delivery | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM resume_deliveries
                 WHERE wait_id = ?
                 ORDER BY created_at DESC
                 LIMIT 1
                """,
                (wait_id,),
            ).fetchone()
        return None if row is None else self._row(row)

    def list(self, *, limit: int = 100) -> list[Delivery]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM resume_deliveries
                 ORDER BY created_at DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row(row) for row in reversed(rows)]

    def due(self, *, now: float | None = None, limit: int = 100) -> list[Delivery]:
        now = time.time() if now is None else now
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM resume_deliveries
                 WHERE status IN ('pending', 'retry')
                   AND next_attempt_at <= ?
                   AND (
                       claimed_by IS NULL
                       OR claim_expires_at IS NULL
                       OR claim_expires_at <= ?
                   )
                 ORDER BY next_attempt_at, created_at
                 LIMIT ?
                """,
                (now, now, limit),
            ).fetchall()
        return [self._row(row) for row in rows]

    def claim_due(
        self,
        *,
        worker: str,
        lease_seconds: float = 30.0,
        now: float | None = None,
    ) -> Delivery | None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        now = time.time() if now is None else now
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM resume_deliveries
                 WHERE status IN ('pending', 'retry')
                   AND next_attempt_at <= ?
                   AND (
                       claimed_by IS NULL
                       OR claim_expires_at IS NULL
                       OR claim_expires_at <= ?
                   )
                 ORDER BY next_attempt_at, created_at
                 LIMIT 1
                """,
                (now, now),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                """
                UPDATE resume_deliveries
                   SET claimed_by = ?, claim_expires_at = ?, updated_at = ?
                 WHERE id = ?
                """,
                (worker, now + lease_seconds, now, row["id"]),
            )
            row = conn.execute(
                "SELECT * FROM resume_deliveries WHERE id = ?",
                (row["id"],),
            ).fetchone()
            assert row is not None
            return self._row(row)

    def mark_success(
        self,
        delivery_id: str,
        *,
        worker: str,
        now: float | None = None,
    ) -> Delivery:
        now = time.time() if now is None else now
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM resume_deliveries WHERE id = ?",
                (delivery_id,),
            ).fetchone()
            if row is None:
                raise KeyError(delivery_id)
            item = self._row(row)
            if item.status == "dispatched":
                return item
            self._require_owner(item, worker, now)
            conn.execute(
                """
                UPDATE resume_deliveries
                   SET status = 'dispatched', attempt = attempt + 1,
                       claimed_by = NULL, claim_expires_at = NULL,
                       last_error = NULL, updated_at = ?
                 WHERE id = ?
                """,
                (now, delivery_id),
            )
            row = conn.execute(
                "SELECT * FROM resume_deliveries WHERE id = ?",
                (delivery_id,),
            ).fetchone()
            assert row is not None
            return self._row(row)

    def mark_failure(
        self,
        delivery_id: str,
        *,
        worker: str,
        error: str,
        now: float | None = None,
    ) -> Delivery:
        now = time.time() if now is None else now
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM resume_deliveries WHERE id = ?",
                (delivery_id,),
            ).fetchone()
            if row is None:
                raise KeyError(delivery_id)
            item = self._row(row)
            self._require_owner(item, worker, now)
            attempt = item.attempt + 1
            if attempt >= item.max_attempts:
                status = "dead_letter"
                next_at = item.next_attempt_at
            else:
                status = "retry"
                delay = min(
                    item.base_delay * (item.multiplier ** (attempt - 1)),
                    item.max_delay,
                )
                next_at = now + delay
            conn.execute(
                """
                UPDATE resume_deliveries
                   SET status = ?, attempt = ?, next_attempt_at = ?,
                       claimed_by = NULL, claim_expires_at = NULL,
                       last_error = ?, updated_at = ?
                 WHERE id = ?
                """,
                (status, attempt, next_at, error, now, delivery_id),
            )
            row = conn.execute(
                "SELECT * FROM resume_deliveries WHERE id = ?",
                (delivery_id,),
            ).fetchone()
            assert row is not None
            return self._row(row)

    @staticmethod
    def _require_owner(item: Delivery, worker: str, now: float) -> None:
        if item.claimed_by != worker:
            raise RuntimeError(f"{item.id} is not claimed by {worker}")
        if item.claim_expires_at is not None and item.claim_expires_at <= now:
            raise RuntimeError(f"{item.id} lease expired")

    @staticmethod
    def _row(row: sqlite3.Row) -> Delivery:
        return Delivery(
            id=row["id"],
            wait_id=row["wait_id"],
            adapter=row["adapter"],
            target=row["target"],
            destination=row["destination"],
            destination_revision=row["destination_revision"],
            destination_changed_by=row["destination_changed_by"],
            destination_change_reason=row["destination_change_reason"],
            allowed_machine_actors=tuple(json.loads(row["allowed_machine_actors_json"])),
            status=row["status"],
            attempt=row["attempt"],
            max_attempts=row["max_attempts"],
            base_delay=row["base_delay"],
            multiplier=row["multiplier"],
            max_delay=row["max_delay"],
            next_attempt_at=row["next_attempt_at"],
            claimed_by=row["claimed_by"],
            claim_expires_at=row["claim_expires_at"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def reconcile_bound_deliveries(
    queue: HumanQueue,
    deliveries: DurableDeliveryQueue,
    destinations: DestinationRegistry | None = None,
) -> list[Delivery]:
    """Materialize any persisted resume bindings missing a delivery job.

    This closes the crash window between DECISION_COMMITTED/RESUME_REQUESTED
    and delivery enqueue. The enqueue operation is idempotent by
    (wait_id, adapter, target), so reconciliation is safe to repeat.
    """
    materialized: list[Delivery] = []
    for item in queue.resume_requested():
        binding = item.resume_binding or {}
        if destinations is None and binding.get("destination"):
            continue
        resolved = (
            resolve_resume_binding(binding, destinations)
            if destinations is not None
            else binding
        )
        adapter = str(resolved.get("adapter") or "").strip()
        target = str(resolved.get("target") or "").strip()
        if not adapter or not target:
            continue
        policy = RetryPolicy(
            max_attempts=int(resolved.get("max_attempts") or 3),
            base_delay=float(resolved.get("base_delay") or 0.25),
            multiplier=float(resolved.get("multiplier") or 2.0),
            max_delay=float(resolved.get("max_delay") or 5.0),
        )
        job = deliveries.enqueue(
            item.id,
            adapter=adapter,
            target=target,
            policy=policy,
            destination=resolved.get("destination"),
            destination_revision=resolved.get("destination_revision"),
            destination_changed_by=resolved.get("destination_changed_by"),
            destination_change_reason=resolved.get("destination_change_reason"),
            allowed_machine_actors=resolved.get("allowed_machine_actors"),
        )
        queue.mark_resume_delivery_queued(
            item.id,
            actor="reconciler",
            adapter=adapter,
            target=target,
            delivery_id=job.id,
            destination=resolved.get("destination"),
            destination_revision=resolved.get("destination_revision"),
            destination_changed_by=resolved.get("destination_changed_by"),
            destination_change_reason=resolved.get("destination_change_reason"),
        )
        materialized.append(job)
    return materialized


def run_delivery_once(
    queue: HumanQueue,
    deliveries: DurableDeliveryQueue,
    adapters: dict[str, ResumeAdapter],
    *,
    worker: str,
    lease_seconds: float = 30.0,
    now: float | None = None,
) -> Delivery | None:
    """Claim and execute one due delivery.

    Adapter credentials remain process-local in the adapter registry; only the
    adapter name and logical target are persisted.
    """
    job = deliveries.claim_due(
        worker=worker,
        lease_seconds=lease_seconds,
        now=now,
    )
    if job is None:
        return None

    adapter = adapters.get(job.adapter)
    if adapter is None:
        failed = deliveries.mark_failure(
            job.id,
            worker=worker,
            error=f"adapter not registered: {job.adapter}",
            now=now,
        )
        queue.record_resume_delivery_event(
            job.wait_id,
            event_type=(
                "RESUME_DEAD_LETTERED"
                if failed.status == "dead_letter"
                else "RESUME_DELIVERY_FAILED"
            ),
            actor=worker,
            adapter=job.adapter,
            target=job.target,
            attempt=failed.attempt,
            error=failed.last_error,
            next_delay=(
                max(
                    0.0,
                    failed.next_attempt_at
                    - (time.time() if now is None else now),
                )
                if failed.status == "retry"
                else None
            ),
        )
        return failed

    queue.record_resume_delivery_event(
        job.wait_id,
        event_type="RESUME_DELIVERY_ATTEMPT",
        actor=worker,
        adapter=job.adapter,
        target=job.target,
        attempt=job.attempt + 1,
    )
    try:
        adapter.dispatch(queue, queue.get(job.wait_id))
    except Exception as exc:
        failed = deliveries.mark_failure(
            job.id,
            worker=worker,
            error=f"{type(exc).__name__}: {exc}",
            now=now,
        )
        queue.record_resume_delivery_event(
            job.wait_id,
            event_type=(
                "RESUME_DEAD_LETTERED"
                if failed.status == "dead_letter"
                else "RESUME_DELIVERY_FAILED"
            ),
            actor=worker,
            adapter=job.adapter,
            target=job.target,
            attempt=failed.attempt,
            error=failed.last_error,
            next_delay=(
                max(
                    0.0,
                    failed.next_attempt_at
                    - (time.time() if now is None else now),
                )
                if failed.status == "retry"
                else None
            ),
        )
        return failed

    return deliveries.mark_success(job.id, worker=worker, now=now)
