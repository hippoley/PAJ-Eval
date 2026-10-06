"""Quorum policies for independently witnessed HumanQueue checkpoints."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Any

from audit_checkpoint import AuditCheckpoint
from audit_witness import (
    CheckpointWitnessProvider,
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
