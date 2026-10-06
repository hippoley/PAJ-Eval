"""External witness support for signed HumanQueue audit checkpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
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
        verifier: HmacWitnessReceiptVerifier,
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
