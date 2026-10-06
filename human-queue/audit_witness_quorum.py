"""Quorum policies for independently witnessed HumanQueue checkpoints."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from dataclasses import asdict, dataclass
from typing import Any

from audit_checkpoint import AuditCheckpoint
from audit_witness import (
    CheckpointWitnessProvider,
    HmacWitnessReceiptVerifier,
    HttpCheckpointWitnessProvider,
    OnlineWitnessReceiptVerifier,
    WitnessReceipt,
    checkpoint_fingerprint,
)


@dataclass(frozen=True)
class WitnessQuorumResult:
    satisfied: bool
    threshold: int
    confirmed_witnesses: tuple[str, ...]
    required_witnesses: tuple[str, ...]
    missing_required_witnesses: tuple[str, ...]
    receipts: tuple[WitnessReceipt, ...]
    failures: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "satisfied": self.satisfied,
            "threshold": self.threshold,
            "confirmed_witnesses": list(self.confirmed_witnesses),
            "required_witnesses": list(self.required_witnesses),
            "missing_required_witnesses": list(
                self.missing_required_witnesses
            ),
            "receipts": [
                asdict(receipt)
                for receipt in self.receipts
            ],
            "failures": dict(self.failures),
        }


class WitnessQuorum:
    """Require a threshold of distinct external witnesses."""

    def __init__(
        self,
        providers: dict[str, CheckpointWitnessProvider],
        *,
        threshold: int,
        required_witnesses: tuple[str, ...] | list[str] = (),
        max_workers: int | None = None,
    ) -> None:
        cleaned = {
            str(name).strip(): provider
            for name, provider in providers.items()
            if str(name).strip()
        }
        if not cleaned:
            raise ValueError("at least one witness provider is required")
        if threshold < 1 or threshold > len(cleaned):
            raise ValueError(
                "witness quorum threshold must be between 1 and provider count"
            )
        required = tuple(
            sorted(
                {
                    str(name).strip()
                    for name in required_witnesses
                    if str(name).strip()
                }
            )
        )
        unknown = set(required) - set(cleaned)
        if unknown:
            raise ValueError(
                "required witnesses are not configured: "
                + ", ".join(sorted(unknown))
            )
        workers = max_workers or len(cleaned)
        if workers < 1:
            raise ValueError("max_workers must be positive")

        self.providers = cleaned
        self.threshold = int(threshold)
        self.required_witnesses = required
        self.max_workers = min(int(workers), len(cleaned))

    def provider_for(
        self,
        witness: str,
    ) -> CheckpointWitnessProvider:
        try:
            return self.providers[witness]
        except KeyError as exc:
            raise KeyError(
                f"unknown witness {witness!r}"
            ) from exc

    @staticmethod
    def _binding_error(
        checkpoint: AuditCheckpoint,
        receipt: WitnessReceipt,
    ) -> str | None:
        if receipt.checkpoint_sequence != checkpoint.sequence:
            return "checkpoint_sequence_mismatch"
        if receipt.checkpoint_signature != checkpoint.signature:
            return "checkpoint_signature_mismatch"
        if receipt.checkpoint_head_hash != checkpoint.head_hash:
            return "checkpoint_head_hash_mismatch"
        if (
            receipt.checkpoint_fingerprint
            != checkpoint_fingerprint(checkpoint)
        ):
            return "checkpoint_fingerprint_mismatch"
        return None

    def _result(
        self,
        *,
        receipts: list[WitnessReceipt],
        failures: dict[str, str],
    ) -> WitnessQuorumResult:
        confirmed = tuple(
            sorted({receipt.witness for receipt in receipts})
        )
        missing_required = tuple(
            name
            for name in self.required_witnesses
            if name not in confirmed
        )
        satisfied = (
            len(confirmed) >= self.threshold
            and not missing_required
        )
        return WitnessQuorumResult(
            satisfied=satisfied,
            threshold=self.threshold,
            confirmed_witnesses=confirmed,
            required_witnesses=self.required_witnesses,
            missing_required_witnesses=missing_required,
            receipts=tuple(
                sorted(
                    receipts,
                    key=lambda item: (
                        item.witness,
                        item.receipt_id,
                    ),
                )
            ),
            failures=dict(sorted(failures.items())),
        )

    def publish(
        self,
        checkpoint: AuditCheckpoint,
    ) -> WitnessQuorumResult:
        receipts: list[WitnessReceipt] = []
        failures: dict[str, str] = {}

        def publish_one(
            expected_witness: str,
            provider: CheckpointWitnessProvider,
        ) -> tuple[str, WitnessReceipt]:
            receipt = provider.publish(checkpoint)
            return expected_witness, receipt

        with ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as pool:
            futures = {
                pool.submit(
                    publish_one,
                    name,
                    provider,
                ): name
                for name, provider in self.providers.items()
            }
            for future in as_completed(futures):
                expected_witness = futures[future]
                try:
                    _, receipt = future.result()
                except Exception as exc:
                    failures[expected_witness] = str(exc)
                    continue

                if receipt.witness != expected_witness:
                    failures[expected_witness] = (
                        "witness_identity_mismatch:"
                        f"{receipt.witness}"
                    )
                    continue
                binding_error = self._binding_error(
                    checkpoint,
                    receipt,
                )
                if binding_error:
                    failures[expected_witness] = binding_error
                    continue
                receipts.append(receipt)

        return self._result(
            receipts=receipts,
            failures=failures,
        )

    def evaluate(
        self,
        checkpoint: AuditCheckpoint,
        receipts: list[WitnessReceipt]
        | tuple[WitnessReceipt, ...],
    ) -> WitnessQuorumResult:
        accepted: list[WitnessReceipt] = []
        failures: dict[str, str] = {}
        seen: set[str] = set()

        for receipt in receipts:
            witness = receipt.witness
            if witness in seen:
                failures.setdefault(
                    witness,
                    "duplicate_witness_receipt",
                )
                continue
            seen.add(witness)

            provider = self.providers.get(witness)
            if provider is None:
                failures[witness] = "unconfigured_witness"
                continue
            binding_error = self._binding_error(
                checkpoint,
                receipt,
            )
            if binding_error:
                failures[witness] = binding_error
                continue
            try:
                valid = provider.verify(receipt)
            except Exception as exc:
                failures[witness] = (
                    "verification_error:" + str(exc)
                )
                continue
            if not valid:
                failures[witness] = "invalid_receipt"
                continue
            accepted.append(receipt)

        return self._result(
            receipts=accepted,
            failures=failures,
        )



def load_witness_quorum() -> WitnessQuorum | None:
    raw = os.environ.get(
        "HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON",
        "",
    ).strip()
    if not raw:
        return None
    try:
        config = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON must contain a JSON object"
        ) from exc
    if not isinstance(config, dict):
        raise ValueError(
            "HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON must contain a JSON object"
        )

    raw_witnesses = config.get("witnesses")
    if not isinstance(raw_witnesses, dict) or not raw_witnesses:
        raise ValueError("witness quorum requires a non-empty witnesses object")

    providers: dict[str, CheckpointWitnessProvider] = {}
    for name, raw_target in raw_witnesses.items():
        witness_name = str(name).strip()
        if not witness_name or not isinstance(raw_target, dict):
            raise ValueError("each witness quorum target must be a named object")

        endpoint = str(raw_target.get("url") or "").strip()
        verify_endpoint = str(
            raw_target.get("verify_url") or ""
        ).strip()
        raw_keys = raw_target.get("keys")
        if not endpoint:
            raise ValueError(
                f"witness {witness_name!r} requires url"
            )
        if bool(verify_endpoint) == bool(raw_keys):
            raise ValueError(
                f"witness {witness_name!r} must configure exactly one "
                "of verify_url or keys"
            )

        timeout = float(raw_target.get("timeout_seconds") or 5)
        if verify_endpoint:
            verifier = OnlineWitnessReceiptVerifier(
                verify_endpoint,
                timeout_seconds=timeout,
            )
        else:
            if not isinstance(raw_keys, dict):
                raise ValueError(
                    f"witness {witness_name!r} keys must be an object"
                )
            verifier = HmacWitnessReceiptVerifier(
                {
                    str(k): str(v)
                    for k, v in raw_keys.items()
                }
            )

        providers[witness_name] = HttpCheckpointWitnessProvider(
            endpoint,
            verifier=verifier,
            timeout_seconds=timeout,
            publish_token=(
                str(raw_target.get("publish_token") or "")
                or None
            ),
        )

    threshold = int(config.get("threshold") or 1)
    required = config.get("required_witnesses") or []
    if not isinstance(required, list):
        raise ValueError("required_witnesses must be an array")

    return WitnessQuorum(
        providers,
        threshold=threshold,
        required_witnesses=[
            str(value)
            for value in required
        ],
        max_workers=(
            int(config["max_workers"])
            if config.get("max_workers") is not None
            else None
        ),
    )
