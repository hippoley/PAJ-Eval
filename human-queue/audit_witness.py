"""External witness support for signed HumanQueue audit checkpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from audit_checkpoint import AuditCheckpoint


@dataclass(frozen=True)
class WitnessReceipt:
    version: int
    witness: str
    receipt_id: str
    received_at: float
    checkpoint_sequence: int
    checkpoint_signature: str
    checkpoint_head_hash: str | None
    key_id: str
    signature: str


class WitnessReceiptVerifier(Protocol):
    def verify(self, receipt: WitnessReceipt) -> bool:
        ...


class CheckpointWitnessProvider(Protocol):
    def publish(self, checkpoint: AuditCheckpoint) -> WitnessReceipt:
        ...

    def verify(self, receipt: WitnessReceipt) -> bool:
        ...


def checkpoint_fingerprint(checkpoint: AuditCheckpoint) -> str:
    payload = json.dumps(
        asdict(checkpoint),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class HmacWitnessReceiptVerifier:
    keys: dict[str, str]

    def __post_init__(self) -> None:
        cleaned = {
            str(kid).strip(): str(secret)
            for kid, secret in self.keys.items()
            if str(kid).strip() and str(secret)
        }
        if not cleaned:
            raise ValueError("witness receipt verification keys are required")
        object.__setattr__(self, "keys", cleaned)

    @staticmethod
    def payload(receipt: WitnessReceipt) -> str:
        return json.dumps(
            {
                "version": receipt.version,
                "witness": receipt.witness,
                "receipt_id": receipt.receipt_id,
                "received_at": receipt.received_at,
                "checkpoint_sequence": receipt.checkpoint_sequence,
                "checkpoint_signature": receipt.checkpoint_signature,
                "checkpoint_head_hash": receipt.checkpoint_head_hash,
                "key_id": receipt.key_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def verify(self, receipt: WitnessReceipt) -> bool:
        key = self.keys.get(receipt.key_id)
        if key is None:
            raise KeyError(receipt.key_id)
        expected = hmac.new(
            key.encode(),
            self.payload(receipt).encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(receipt.signature, expected)


class OnlineWitnessReceiptVerifier:
    """Ask an independent witness service to validate its own receipt."""

    def __init__(
        self,
        endpoint: str,
        *,
        timeout_seconds: float = 5.0,
    ) -> None:
        endpoint = endpoint.strip()
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError(
                "witness verification endpoint must be http or https"
            )
        if timeout_seconds <= 0:
            raise ValueError("witness verification timeout_seconds must be > 0")
        self.endpoint = endpoint
        self.timeout_seconds = float(timeout_seconds)

    def verify(self, receipt: WitnessReceipt) -> bool:
        body = json.dumps(
            {"receipt": asdict(receipt)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        request = urllib.request.Request(
            self.endpoint,
            method="POST",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                if response.status < 200 or response.status >= 300:
                    raise RuntimeError(
                        f"witness verification returned HTTP {response.status}"
                    )
                payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"witness verification returned HTTP {exc.code}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(
                "witness verification request failed"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "witness verification returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict) or "valid" not in payload:
            raise RuntimeError(
                "witness verification returned invalid response"
            )
        return payload.get("valid") is True


class HttpCheckpointWitnessProvider:
    """Publish checkpoints to an independent HTTP witness.

    The remote service returns a signed receipt. HumanQueue verifies that
    receipt with a witness verification key that is separate from the
    checkpoint signing key.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        verifier: WitnessReceiptVerifier,
        timeout_seconds: float = 5.0,
    ) -> None:
        endpoint = endpoint.strip()
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("witness endpoint must be http or https")
        if timeout_seconds <= 0:
            raise ValueError("witness timeout_seconds must be > 0")
        self.endpoint = endpoint
        self.verifier = verifier
        self.timeout_seconds = float(timeout_seconds)

    def publish(self, checkpoint: AuditCheckpoint) -> WitnessReceipt:
        body = json.dumps(
            {
                "checkpoint": asdict(checkpoint),
                "checkpoint_fingerprint": checkpoint_fingerprint(checkpoint),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        request = urllib.request.Request(
            self.endpoint,
            method="POST",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                if response.status < 200 or response.status >= 300:
                    raise RuntimeError(
                        f"witness returned HTTP {response.status}"
                    )
                payload = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"witness returned HTTP {exc.code}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError("witness request failed") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("witness returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("witness returned invalid receipt")
        raw_receipt = payload.get("receipt")
        if not isinstance(raw_receipt, dict):
            raise RuntimeError("witness response missing receipt")

        try:
            receipt = WitnessReceipt(**raw_receipt)
        except TypeError as exc:
            raise RuntimeError("witness receipt shape is invalid") from exc

        if receipt.checkpoint_sequence != checkpoint.sequence:
            raise RuntimeError("witness receipt sequence mismatch")
        if receipt.checkpoint_signature != checkpoint.signature:
            raise RuntimeError("witness receipt checkpoint signature mismatch")
        if receipt.checkpoint_head_hash != checkpoint.head_hash:
            raise RuntimeError("witness receipt checkpoint head mismatch")
        if not self.verify(receipt):
            raise RuntimeError("witness receipt signature is invalid")
        return receipt

    def verify(self, receipt: WitnessReceipt) -> bool:
        try:
            return self.verifier.verify(receipt)
        except KeyError:
            return False


class InMemoryWitnessProvider:
    """Minimal test/development witness with an independent receipt key."""

    def __init__(
        self,
        *,
        witness: str = "memory-witness",
        key_id: str = "w1",
        key: str,
    ) -> None:
        if not witness.strip() or not key_id.strip() or not key:
            raise ValueError("witness, key_id, and key are required")
        self.witness = witness.strip()
        self.key_id = key_id.strip()
        self.key = key
        self._receipts: list[WitnessReceipt] = []

    def publish(self, checkpoint: AuditCheckpoint) -> WitnessReceipt:
        unsigned = WitnessReceipt(
            version=1,
            witness=self.witness,
            receipt_id=f"receipt-{len(self._receipts) + 1}",
            received_at=time.time(),
            checkpoint_sequence=checkpoint.sequence,
            checkpoint_signature=checkpoint.signature,
            checkpoint_head_hash=checkpoint.head_hash,
            key_id=self.key_id,
            signature="",
        )
        payload = HmacWitnessReceiptVerifier.payload(unsigned)
        signature = hmac.new(
            self.key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        receipt = WitnessReceipt(
            **{
                **asdict(unsigned),
                "signature": signature,
            }
        )
        self._receipts.append(receipt)
        return receipt

    def verify(self, receipt: WitnessReceipt) -> bool:
        verifier = HmacWitnessReceiptVerifier(
            {self.key_id: self.key}
        )
        return verifier.verify(receipt)

    @property
    def receipts(self) -> tuple[WitnessReceipt, ...]:
        return tuple(self._receipts)



def load_witness_provider() -> CheckpointWitnessProvider | None:
    endpoint = os.environ.get("HUMANQUEUE_AUDIT_WITNESS_URL", "").strip()
    verify_endpoint = os.environ.get(
        "HUMANQUEUE_AUDIT_WITNESS_VERIFY_URL",
        "",
    ).strip()
    raw_keys = os.environ.get("HUMANQUEUE_AUDIT_WITNESS_KEYS", "").strip()

    if not endpoint and not verify_endpoint and not raw_keys:
        return None
    if not endpoint:
        raise ValueError(
            "HUMANQUEUE_AUDIT_WITNESS_URL is required when witness is configured"
        )

    timeout = float(
        os.environ.get(
            "HUMANQUEUE_AUDIT_WITNESS_TIMEOUT_SECONDS",
            "5",
        )
    )

    if verify_endpoint:
        verifier: WitnessReceiptVerifier = OnlineWitnessReceiptVerifier(
            verify_endpoint,
            timeout_seconds=timeout,
        )
    else:
        if not raw_keys:
            raise ValueError(
                "configure HUMANQUEUE_AUDIT_WITNESS_VERIFY_URL for an independent "
                "online witness, or HUMANQUEUE_AUDIT_WITNESS_KEYS for shared-key verification"
            )
        try:
            parsed = json.loads(raw_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "HUMANQUEUE_AUDIT_WITNESS_KEYS must contain a JSON object"
            ) from exc
        if not isinstance(parsed, dict):
            raise ValueError(
                "HUMANQUEUE_AUDIT_WITNESS_KEYS must contain a JSON object"
            )
        verifier = HmacWitnessReceiptVerifier(
            {str(k): str(v) for k, v in parsed.items()}
        )

    return HttpCheckpointWitnessProvider(
        endpoint,
        verifier=verifier,
        timeout_seconds=timeout,
    )




class WitnessReceiptJournal:
    """Local cache of independently signed witness receipts."""

    def __init__(
        self,
        path: str | Path,
        *,
        lock_timeout_seconds: float = 5.0,
        stale_lock_seconds: float = 60.0,
    ) -> None:
        if lock_timeout_seconds <= 0:
            raise ValueError("witness journal lock_timeout_seconds must be > 0")
        if stale_lock_seconds <= 0:
            raise ValueError("witness journal stale_lock_seconds must be > 0")
        self.path = Path(path)
        self.lock_timeout_seconds = float(lock_timeout_seconds)
        self.stale_lock_seconds = float(stale_lock_seconds)

    @property
    def lock_path(self) -> Path:
        return Path(str(self.path) + ".lock")

    @contextmanager
    def _file_lock(self):
        deadline = time.monotonic() + self.lock_timeout_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)

        while True:
            try:
                fd = os.open(
                    self.lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                try:
                    os.write(
                        fd,
                        json.dumps(
                            {
                                "pid": os.getpid(),
                                "created_at": time.time(),
                            },
                            sort_keys=True,
                        ).encode(),
                    )
                finally:
                    os.close(fd)
                break
            except FileExistsError:
                try:
                    age = time.time() - self.lock_path.stat().st_mtime
                except FileNotFoundError:
                    continue
                if age > self.stale_lock_seconds:
                    try:
                        self.lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "timed out waiting for witness receipt journal lock"
                    )
                time.sleep(0.05)

        try:
            yield
        finally:
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass

    def receipts(self) -> list[WitnessReceipt]:
        if not self.path.exists():
            return []
        receipts: list[WitnessReceipt] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"invalid witness receipt JSON at line {line_number}"
                    ) from exc
                if not isinstance(raw, dict):
                    raise RuntimeError(
                        f"invalid witness receipt at line {line_number}"
                    )
                try:
                    receipts.append(WitnessReceipt(**raw))
                except TypeError as exc:
                    raise RuntimeError(
                        f"invalid witness receipt shape at line {line_number}"
                    ) from exc
        return receipts

    def append(
        self,
        receipt: WitnessReceipt,
        *,
        provider: CheckpointWitnessProvider,
        already_verified: bool = False,
    ) -> WitnessReceipt:
        if not already_verified and not provider.verify(receipt):
            raise RuntimeError("cannot persist invalid witness receipt")

        with self._file_lock():
            existing = self.receipts()
            for current in existing:
                if current.receipt_id == receipt.receipt_id:
                    if current == receipt:
                        return current
                    raise RuntimeError(
                        "witness receipt id conflicts with existing receipt"
                    )

            if (
                existing
                and receipt.checkpoint_sequence
                < existing[-1].checkpoint_sequence
            ):
                raise RuntimeError(
                    "witness receipt checkpoint sequence moved backwards"
                )

            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        asdict(receipt),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())
        return receipt

    def status(
        self,
        checkpoint: AuditCheckpoint | None,
        *,
        provider: CheckpointWitnessProvider,
    ) -> dict[str, Any]:
        try:
            receipts = self.receipts()
        except RuntimeError as exc:
            return {
                "ok": False,
                "reason": "invalid_witness_receipt_journal",
                "detail": str(exc),
            }

        for receipt in receipts:
            try:
                valid = provider.verify(receipt)
            except RuntimeError as exc:
                return {
                    "ok": False,
                    "reason": "witness_verification_unavailable",
                    "receipt_id": receipt.receipt_id,
                    "detail": str(exc),
                }
            except Exception:
                valid = False
            if not valid:
                return {
                    "ok": False,
                    "reason": "invalid_witness_receipt_signature",
                    "receipt_id": receipt.receipt_id,
                }

        if checkpoint is None:
            return {
                "ok": True,
                "witnessed": False,
                "receipt_count": len(receipts),
                "checkpoint_sequence": None,
            }

        matching = [
            receipt
            for receipt in receipts
            if receipt.checkpoint_sequence == checkpoint.sequence
            and receipt.checkpoint_signature == checkpoint.signature
            and receipt.checkpoint_head_hash == checkpoint.head_hash
        ]
        latest = matching[-1] if matching else None
        return {
            "ok": True,
            "witnessed": latest is not None,
            "receipt_count": len(receipts),
            "checkpoint_sequence": checkpoint.sequence,
            "receipt": asdict(latest) if latest else None,
        }


def load_witness_receipt_journal() -> WitnessReceiptJournal | None:
    path = os.environ.get(
        "HUMANQUEUE_AUDIT_WITNESS_RECEIPTS_FILE",
        "",
    ).strip()
    if not path:
        return None
    return WitnessReceiptJournal(
        path,
        lock_timeout_seconds=float(
            os.environ.get(
                "HUMANQUEUE_AUDIT_WITNESS_RECEIPT_LOCK_TIMEOUT_SECONDS",
                "5",
            )
        ),
        stale_lock_seconds=float(
            os.environ.get(
                "HUMANQUEUE_AUDIT_WITNESS_RECEIPT_STALE_LOCK_SECONDS",
                "60",
            )
        ),
    )
