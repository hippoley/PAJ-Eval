"""Named, secret-free resume destinations for HumanQueue."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adapters import RetryPolicy, sanitize_target


@dataclass(frozen=True)
class ResumeDestination:
    name: str
    adapter: str
    target: str
    policy: RetryPolicy
    enabled: bool
    revision: int
    changed_by: str | None
    change_reason: str | None
    created_at: float
    updated_at: float

    def snapshot(self) -> dict[str, Any]:
        return {
            "destination": self.name,
            "adapter": self.adapter,
            "target": self.target,
            "destination_revision": self.revision,
            "destination_changed_by": self.changed_by,
            "destination_change_reason": self.change_reason,
            "max_attempts": self.policy.max_attempts,
            "base_delay": self.policy.base_delay,
            "multiplier": self.policy.multiplier,
            "max_delay": self.policy.max_delay,
        }


class DestinationRegistry:
    """SQLite-backed registry of logical resume destinations.

    Secrets are deliberately excluded. Adapter credentials stay process-local
    in the delivery worker.
    """

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
                CREATE TABLE IF NOT EXISTS resume_destinations (
                    name TEXT PRIMARY KEY,
                    adapter TEXT NOT NULL,
                    target TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1,
                    changed_by TEXT,
                    change_reason TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(resume_destinations)"
                ).fetchall()
            }
            if "revision" not in columns:
                conn.execute(
                    "ALTER TABLE resume_destinations "
                    "ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"
                )
            if "changed_by" not in columns:
                conn.execute(
                    "ALTER TABLE resume_destinations ADD COLUMN changed_by TEXT"
                )
            if "change_reason" not in columns:
                conn.execute(
                    "ALTER TABLE resume_destinations ADD COLUMN change_reason TEXT"
                )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS resume_destination_revisions (
                    name TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    adapter TEXT NOT NULL,
                    target TEXT NOT NULL,
                    policy_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    changed_by TEXT,
                    change_reason TEXT,
                    changed_at REAL NOT NULL,
                    PRIMARY KEY(name, revision)
                )
                """
            )

    def put(
        self,
        name: str,
        *,
        adapter: str,
        target: str,
        policy: RetryPolicy | None = None,
        enabled: bool = True,
        actor: str = "system",
        reason: str | None = None,
        now: float | None = None,
    ) -> ResumeDestination:
        name = name.strip()
        adapter = adapter.strip()
        target = target.strip()
        if adapter == "webhook":
            target = sanitize_target(target)
        if not name:
            raise ValueError("destination name is required")
        if not adapter:
            raise ValueError("destination adapter is required")
        if not target:
            raise ValueError("destination target is required")
        policy = policy or RetryPolicy()
        if policy.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        actor = actor.strip()
        if not actor:
            raise ValueError("destination change actor is required")
        reason = reason.strip() if isinstance(reason, str) else reason
        now = time.time() if now is None else now
        policy_json = json.dumps(
            {
                "max_attempts": policy.max_attempts,
                "base_delay": policy.base_delay,
                "multiplier": policy.multiplier,
                "max_delay": policy.max_delay,
            },
            sort_keys=True,
        )
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM resume_destinations WHERE name = ?",
                (name,),
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            enabled_int = 1 if enabled else 0
            changed = (
                existing is None
                or existing["adapter"] != adapter
                or existing["target"] != target
                or existing["policy_json"] != policy_json
                or existing["enabled"] != enabled_int
            )
            if existing is not None and not changed:
                return self._row(existing)
            revision = 1 if existing is None else int(existing["revision"]) + 1
            conn.execute(
                """
                INSERT INTO resume_destinations (
                    name, adapter, target, policy_json, enabled, revision,
                    changed_by, change_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    adapter = excluded.adapter,
                    target = excluded.target,
                    policy_json = excluded.policy_json,
                    enabled = excluded.enabled,
                    revision = excluded.revision,
                    changed_by = excluded.changed_by,
                    change_reason = excluded.change_reason,
                    updated_at = excluded.updated_at
                """,
                (
                    name,
                    adapter,
                    target,
                    policy_json,
                    enabled_int,
                    revision,
                    actor,
                    reason,
                    created_at,
                    now,
                ),
            )
            if changed:
                conn.execute(
                    """
                    INSERT INTO resume_destination_revisions (
                        name, revision, adapter, target, policy_json,
                        enabled, changed_by, change_reason, changed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        revision,
                        adapter,
                        target,
                        policy_json,
                        enabled_int,
                        actor,
                        reason,
                        now,
                    ),
                )
            row = conn.execute(
                "SELECT * FROM resume_destinations WHERE name = ?",
                (name,),
            ).fetchone()
            assert row is not None
            return self._row(row)

    def get(self, name: str, *, require_enabled: bool = False) -> ResumeDestination:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM resume_destinations WHERE name = ?",
                (name,),
            ).fetchone()
            if row is None:
                raise KeyError(name)
            item = self._row(row)
        if require_enabled and not item.enabled:
            raise RuntimeError(f"destination {name} is disabled")
        return item

    def list(self) -> list[ResumeDestination]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM resume_destinations ORDER BY name"
            ).fetchall()
        return [self._row(row) for row in rows]

    def set_enabled(
        self,
        name: str,
        enabled: bool,
        *,
        actor: str = "system",
        reason: str | None = None,
        now: float | None = None,
    ) -> ResumeDestination:
        now = time.time() if now is None else now
        current = self.get(name)
        return self.put(
            name,
            adapter=current.adapter,
            target=current.target,
            policy=current.policy,
            enabled=enabled,
            actor=actor,
            reason=reason,
            now=now,
        )

    def history(self, name: str) -> list[ResumeDestination]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT name, adapter, target, policy_json, enabled,
                       revision, changed_by, change_reason,
                       changed_at AS created_at, changed_at AS updated_at
                  FROM resume_destination_revisions
                 WHERE name = ?
                 ORDER BY revision
                """,
                (name,),
            ).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> ResumeDestination:
        policy = json.loads(row["policy_json"])
        return ResumeDestination(
            name=row["name"],
            adapter=row["adapter"],
            target=row["target"],
            policy=RetryPolicy(
                max_attempts=int(policy["max_attempts"]),
                base_delay=float(policy["base_delay"]),
                multiplier=float(policy["multiplier"]),
                max_delay=float(policy["max_delay"]),
            ),
            enabled=bool(row["enabled"]),
            revision=int(row["revision"]),
            changed_by=row["changed_by"],
            change_reason=row["change_reason"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def resolve_resume_binding(
    binding: dict[str, Any],
    registry: DestinationRegistry,
) -> dict[str, Any]:
    """Resolve a logical binding to an immutable delivery snapshot."""
    destination_name = str(binding.get("destination") or "").strip()
    if destination_name:
        destination = registry.get(destination_name, require_enabled=True)
        return destination.snapshot()

    adapter = str(binding.get("adapter") or "").strip()
    target = str(binding.get("target") or "").strip()
    if not adapter or not target:
        raise ValueError(
            "resume_binding requires destination or adapter + target"
        )
    policy = RetryPolicy(
        max_attempts=int(binding.get("max_attempts") or 3),
        base_delay=float(binding.get("base_delay") or 0.25),
        multiplier=float(binding.get("multiplier") or 2.0),
        max_delay=float(binding.get("max_delay") or 5.0),
    )
    if policy.max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    return {
        "adapter": adapter,
        "target": target,
        "max_attempts": policy.max_attempts,
        "base_delay": policy.base_delay,
        "multiplier": policy.multiplier,
        "max_delay": policy.max_delay,
    }
