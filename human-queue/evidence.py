"""Stable evidence snapshots for HumanQueue provenance."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from typing import Any

from audit_checkpoint import AuditCheckpointSigner
from audit_witness import (
    CheckpointWitnessProvider,
    WitnessReceiptJournal,
)
from audit_witness_quorum import WitnessQuorum
from runtime import HumanQueue


EVIDENCE_SCHEMA = "humanqueue.evidence.v1"


def _canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def build_evidence_snapshot(
    queue: HumanQueue,
    *,
    checkpoint_signer: AuditCheckpointSigner | None = None,
    witness_provider: CheckpointWitnessProvider | None = None,
    witness_receipts: WitnessReceiptJournal | None = None,
    witness_quorum: WitnessQuorum | None = None,
    generated_at: float | None = None,
) -> dict[str, Any]:
    audit = queue.verify_audit_chain()

    checkpoint = (
        checkpoint_signer.latest()
        if checkpoint_signer is not None
        else None
    )
    checkpoint_verification = (
        checkpoint_signer.verify()
        if checkpoint_signer is not None
        else {
            "ok": True,
            "configured": False,
            "anchored": False,
        }
    )

    receipts: list[Any] = []
    receipt_error: str | None = None
    if witness_receipts is not None:
        try:
            receipts = witness_receipts.receipts()
        except RuntimeError as exc:
            receipt_error = str(exc)

    if witness_provider is None:
        single_witness = {
            "ok": True,
            "configured": False,
            "journal_configured": witness_receipts is not None,
            "witnessed": False,
        }
    elif witness_receipts is None:
        single_witness = {
            "ok": True,
            "configured": True,
            "journal_configured": False,
            "witnessed": False,
        }
    elif receipt_error is not None:
        single_witness = {
            "ok": False,
            "configured": True,
            "journal_configured": True,
            "witnessed": False,
            "reason": "invalid_witness_receipt_journal",
            "detail": receipt_error,
        }
    else:
        single_witness = {
            "configured": True,
            "journal_configured": True,
            **witness_receipts.status(
                checkpoint,
                provider=witness_provider,
            ),
        }

    if witness_quorum is None:
        quorum = {
            "ok": True,
            "configured": False,
            "satisfied": False,
        }
    elif checkpoint is None:
        quorum = {
            "ok": True,
            "configured": True,
            "satisfied": False,
            "checkpoint_sequence": None,
        }
    elif witness_receipts is None:
        quorum = {
            "ok": False,
            "configured": True,
            "satisfied": False,
            "reason": "witness_receipt_journal_not_configured",
            "checkpoint_sequence": checkpoint.sequence,
            "threshold": witness_quorum.threshold,
            "required_witnesses": list(
                witness_quorum.required_witnesses
            ),
        }
    elif receipt_error is not None:
        quorum = {
            "ok": False,
            "configured": True,
            "satisfied": False,
            "reason": "invalid_witness_receipt_journal",
            "detail": receipt_error,
            "checkpoint_sequence": checkpoint.sequence,
            "threshold": witness_quorum.threshold,
            "required_witnesses": list(
                witness_quorum.required_witnesses
            ),
        }
    else:
        result = witness_quorum.evaluate(
            checkpoint,
            receipts,
        )
        quorum = {
            "ok": result.satisfied,
            "configured": True,
            "checkpoint_sequence": checkpoint.sequence,
            **result.to_dict(),
        }

    policy_ok = bool(
        audit.get("ok")
        and checkpoint_verification.get("ok")
        and single_witness.get("ok")
        and quorum.get("ok")
    )

    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "audit_chain": audit,
        "checkpoint": {
            "configured": checkpoint_signer is not None,
            "latest": (
                asdict(checkpoint)
                if checkpoint is not None
                else None
            ),
            "verification": checkpoint_verification,
        },
        "witness": {
            "status": single_witness,
            "receipt_count": len(receipts),
            "receipts": [
                asdict(receipt)
                for receipt in receipts
            ],
        },
        "quorum": quorum,
        "policy_ok": policy_ok,
    }
    evidence_id = _canonical_hash(evidence)

    return {
        **evidence,
        "evidence_id": evidence_id,
        "generated_at": (
            time.time()
            if generated_at is None
            else float(generated_at)
        ),
    }
