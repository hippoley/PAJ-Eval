"""Externally anchored audit checkpoints for HumanQueue.

The checkpoint file is deliberately separate from SQLite. Its HMAC key is
process configuration only and is never persisted in either the database or
checkpoint file.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from runtime import HumanQueue


@dataclass(frozen=True)
class AuditCheckpoint:
    version: int
    sequence: int
    created_at: float
    event_count: int
    head_hash: str | None
    previous_signature: str | None
    key_id: str
    signature: str


class AuditCheckpointSigner:
    """Append and verify signed audit-head checkpoints outside SQLite."""

    def __init__(
        self,
        queue: HumanQueue,
        checkpoint_path: str | Path,
        *,
        key: str,
        key_id: str = "default",
    ) -> None:
        if not key:
            raise ValueError("audit checkpoint signing key is required")
        if not key_id.strip():
            raise ValueError("audit checkpoint key_id is required")
        self.queue = queue
        self.checkpoint_path = Path(checkpoint_path)
        self.key = key
        self.key_id = key_id.strip()
        self._lock = threading.Lock()

    @classmethod
    def from_env(
        cls,
        queue: HumanQueue,
    ) -> "AuditCheckpointSigner | None":
        path = os.environ.get("HUMANQUEUE_AUDIT_CHECKPOINT_FILE", "").strip()
        key = os.environ.get("HUMANQUEUE_AUDIT_CHECKPOINT_KEY", "")
        if not path and not key:
            return None
        if not path:
            raise ValueError(
                "HUMANQUEUE_AUDIT_CHECKPOINT_FILE is required when checkpoint signing is enabled"
            )
        if not key:
            raise ValueError(
                "HUMANQUEUE_AUDIT_CHECKPOINT_KEY is required when checkpoint signing is enabled"
            )
        return cls(
            queue,
            path,
            key=key,
            key_id=os.environ.get(
                "HUMANQUEUE_AUDIT_CHECKPOINT_KEY_ID",
                "default",
            ),
        )

    @staticmethod
    def _payload(
        *,
        version: int,
        sequence: int,
        created_at: float,
        event_count: int,
        head_hash: str | None,
        previous_signature: str | None,
        key_id: str,
    ) -> str:
        return json.dumps(
            {
                "version": version,
                "sequence": sequence,
                "created_at": created_at,
                "event_count": event_count,
                "head_hash": head_hash,
                "previous_signature": previous_signature,
                "key_id": key_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def _sign_payload(self, payload: str) -> str:
        return hmac.new(
            self.key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _read_raw(self) -> list[dict[str, Any]]:
        if not self.checkpoint_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.checkpoint_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"invalid checkpoint JSON at line {line_number}"
                    ) from exc
                if not isinstance(value, dict):
                    raise RuntimeError(
                        f"invalid checkpoint object at line {line_number}"
                    )
                rows.append(value)
        return rows

    def checkpoints(self) -> list[AuditCheckpoint]:
        return [AuditCheckpoint(**row) for row in self._read_raw()]

    def create(self, *, now: float | None = None) -> AuditCheckpoint:
        with self._lock:
            chain = self.queue.verify_audit_chain()
            if not chain["ok"]:
                raise RuntimeError(
                    "cannot checkpoint a broken audit chain"
                )

            existing = self.checkpoints()
            previous_signature = (
                existing[-1].signature if existing else None
            )
            checkpoint = AuditCheckpoint(
                version=1,
                sequence=len(existing) + 1,
                created_at=time.time() if now is None else now,
                event_count=int(chain["checked"]),
                head_hash=chain.get("head_hash"),
                previous_signature=previous_signature,
                key_id=self.key_id,
                signature="",
            )
            payload = self._payload(
                version=checkpoint.version,
                sequence=checkpoint.sequence,
                created_at=checkpoint.created_at,
                event_count=checkpoint.event_count,
                head_hash=checkpoint.head_hash,
                previous_signature=checkpoint.previous_signature,
                key_id=checkpoint.key_id,
            )
            signed = AuditCheckpoint(
                **{
                    **asdict(checkpoint),
                    "signature": self._sign_payload(payload),
                }
            )

            self.checkpoint_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            with self.checkpoint_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        asdict(signed),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
            return signed

    def verify(self) -> dict[str, Any]:
        try:
            checkpoints = self.checkpoints()
        except (RuntimeError, TypeError, ValueError) as exc:
            return {
                "ok": False,
                "reason": "invalid_checkpoint_file",
                "detail": str(exc),
            }

        previous_signature: str | None = None
        for index, checkpoint in enumerate(checkpoints, start=1):
            if checkpoint.version != 1:
                return {
                    "ok": False,
                    "reason": "unsupported_checkpoint_version",
                    "checkpoint_sequence": checkpoint.sequence,
                }
            if checkpoint.sequence != index:
                return {
                    "ok": False,
                    "reason": "checkpoint_sequence_gap",
                    "checkpoint_sequence": checkpoint.sequence,
                    "expected_sequence": index,
                }
            if checkpoint.previous_signature != previous_signature:
                return {
                    "ok": False,
                    "reason": "checkpoint_chain_broken",
                    "checkpoint_sequence": checkpoint.sequence,
                }
            payload = self._payload(
                version=checkpoint.version,
                sequence=checkpoint.sequence,
                created_at=checkpoint.created_at,
                event_count=checkpoint.event_count,
                head_hash=checkpoint.head_hash,
                previous_signature=checkpoint.previous_signature,
                key_id=checkpoint.key_id,
            )
            expected_signature = self._sign_payload(payload)
            if not hmac.compare_digest(
                checkpoint.signature,
                expected_signature,
            ):
                return {
                    "ok": False,
                    "reason": "invalid_checkpoint_signature",
                    "checkpoint_sequence": checkpoint.sequence,
                }
            previous_signature = checkpoint.signature

        chain = self.queue.verify_audit_chain()
        if not chain["ok"]:
            return {
                "ok": False,
                "reason": "audit_chain_broken",
                "audit": chain,
                "checkpoint_count": len(checkpoints),
            }

        if not checkpoints:
            return {
                "ok": True,
                "checkpoint_count": 0,
                "audit": chain,
                "anchored": False,
            }

        latest = checkpoints[-1]
        current_count = int(chain["checked"])
        current_head = chain.get("head_hash")
        if current_count < latest.event_count:
            return {
                "ok": False,
                "reason": "audit_history_truncated_before_checkpoint",
                "checkpoint_count": len(checkpoints),
                "checkpoint_event_count": latest.event_count,
                "current_event_count": current_count,
            }

        if current_count == latest.event_count and current_head != latest.head_hash:
            return {
                "ok": False,
                "reason": "audit_head_mismatch_at_checkpoint",
                "checkpoint_count": len(checkpoints),
                "checkpoint_head_hash": latest.head_hash,
                "current_head_hash": current_head,
            }

        if current_count > latest.event_count:
            # Recompute the historical head at the checkpoint boundary.
            with self.queue._connect() as conn:
                row = conn.execute(
                    """
                    SELECT event_hash
                      FROM audit_events
                     ORDER BY id
                     LIMIT 1 OFFSET ?
                    """,
                    (latest.event_count - 1,),
                ).fetchone()
            boundary_hash = row["event_hash"] if row else None
            if boundary_hash != latest.head_hash:
                return {
                    "ok": False,
                    "reason": "audit_checkpoint_boundary_mismatch",
                    "checkpoint_count": len(checkpoints),
                    "checkpoint_head_hash": latest.head_hash,
                    "boundary_hash": boundary_hash,
                }

        return {
            "ok": True,
            "anchored": True,
            "checkpoint_count": len(checkpoints),
            "latest": asdict(latest),
            "audit": chain,
        }
