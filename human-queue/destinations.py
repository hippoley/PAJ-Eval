"""Named, secret-free resume destinations for HumanQueue."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adapters import RetryPolicy


@dataclass(frozen=True)
class ResumeDestination:
    name: str
    adapter: str
    target: str
    policy: RetryPolicy
    enabled: bool
    created_at: float
    updated_at: float

    def snapshot(self) -> dict[str, Any]:
        return {
            "destination": self.name,
            "adapter": self.adapter,
            "target": self.target,
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
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
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
        now: float | None = None,
    ) -> ResumeDestination:
        name = name.strip()
        adapter = adapter.strip()
        target = target.strip()
        if not name:
            raise ValueError("destination name is required")
        if not adapter:
            raise ValueError("destination adapter is required")
        if not target:
            raise ValueError("destination target is required")
        policy = policy or RetryPolicy()
        if policy.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
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
                "SELECT created_at FROM resume_destinations WHERE name = ?",
                (name,),
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO resume_destinations (
                    name, adapter, target, policy_json, enabled,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    adapter = excluded.adapter,
                    target = excluded.target,
                    policy_json = excluded.policy_json,
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
                """,
                (
                    name,
                    adapter,
                    target,
                    policy_json,
                    1 if enabled else 0,
                    created_at,
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
        now: float | None = None,
    ) -> ResumeDestination:
        now = time.time() if now is None else now
        with self._connect() as conn:
            result = conn.execute(
                """
                UPDATE resume_destinations
                   SET enabled = ?, updated_at = ?
                 WHERE name = ?
                """,
                (1 if enabled else 0, now, name),
            )
            if result.rowcount == 0:
                raise KeyError(name)
            row = conn.execute(
                "SELECT * FROM resume_destinations WHERE name = ?",
                (name,),
            ).fetchone()
            assert row is not None
            return self._row(row)

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
