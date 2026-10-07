"""Export and offline verification for HumanQueue evidence bundles."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from audit_checkpoint import AuditCheckpointSigner
from audit_witness import WitnessReceiptJournal, checkpoint_fingerprint
from evidence import build_evidence_snapshot
from runtime import HumanQueue


BUNDLE_SCHEMA = "humanqueue.evidence-bundle.v1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(raw).hexdigest()


def _audit_event_hash(
    *,
    event_id: int,
    wait_id: str,
    event_type: str,
    actor: str | None,
    created_at: float,
    data_json: str,
    prev_hash: str | None,
) -> str:
    canonical = json.dumps(
        {
            "id": event_id,
            "wait_id": wait_id,
            "event_type": event_type,
            "actor": actor,
            "created_at": created_at,
            "data_json": data_json,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def export_evidence_bundle(
    queue: HumanQueue,
    *,
    checkpoint_signer: AuditCheckpointSigner | None = None,
    witness_receipts: WitnessReceiptJournal | None = None,
    exported_at: float | None = None,
) -> dict[str, Any]:
    audit_records = queue.audit_chain_records()
    checkpoints = (
        [
            asdict(checkpoint)
            for checkpoint in checkpoint_signer.checkpoints()
        ]
        if checkpoint_signer is not None
        else []
    )
    receipts = (
        [
            asdict(receipt)
            for receipt in witness_receipts.receipts()
        ]
        if witness_receipts is not None
        else []
    )
    snapshot = build_evidence_snapshot(
        queue,
        checkpoint_signer=checkpoint_signer,
        witness_receipts=witness_receipts,
        generated_at=0,
    )
    snapshot.pop("generated_at", None)

    core = {
        "schema": BUNDLE_SCHEMA,
        "audit_records": audit_records,
        "checkpoints": checkpoints,
        "witness_receipts": receipts,
        "snapshot": snapshot,
    }
    return {
        **core,
        "bundle_id": _canonical_hash(core),
        "exported_at": (
            time.time()
            if exported_at is None
            else float(exported_at)
        ),
    }


def _verify_audit_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    prev_hash: str | None = None
    previous_id: int | None = None

    for index, record in enumerate(records, start=1):
        try:
            event_id = int(record["id"])
            wait_id = str(record["wait_id"])
            event_type = str(record["event_type"])
            actor = record.get("actor")
            created_at = float(record["created_at"])
            data_json = str(record["data_json"])
            actual_prev_hash = record.get("prev_hash")
            actual_event_hash = record.get("event_hash")
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "ok": False,
                "reason": "invalid_audit_record",
                "record_index": index,
                "detail": str(exc),
            }

        if previous_id is not None and event_id <= previous_id:
            return {
                "ok": False,
                "reason": "audit_event_ids_not_strictly_increasing",
                "record_index": index,
                "event_id": event_id,
                "previous_event_id": previous_id,
            }

        expected = _audit_event_hash(
            event_id=event_id,
            wait_id=wait_id,
            event_type=event_type,
            actor=actor,
            created_at=created_at,
            data_json=data_json,
            prev_hash=prev_hash,
        )
        if actual_prev_hash != prev_hash:
            return {
                "ok": False,
                "reason": "audit_prev_hash_mismatch",
                "record_index": index,
                "event_id": event_id,
                "expected_prev_hash": prev_hash,
                "actual_prev_hash": actual_prev_hash,
            }
        if actual_event_hash != expected:
            return {
                "ok": False,
                "reason": "audit_event_hash_mismatch",
                "record_index": index,
                "event_id": event_id,
                "expected_event_hash": expected,
                "actual_event_hash": actual_event_hash,
            }

        prev_hash = actual_event_hash
        previous_id = event_id

    return {
        "ok": True,
        "checked": len(records),
        "head_hash": prev_hash,
    }


def _verify_checkpoint_bindings(
    checkpoints: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    previous_signature: str | None = None

    for expected_sequence, checkpoint in enumerate(
        checkpoints,
        start=1,
    ):
        try:
            sequence = int(checkpoint["sequence"])
            event_count = int(checkpoint["event_count"])
            head_hash = checkpoint.get("head_hash")
            signature = str(checkpoint["signature"])
            linked_previous = checkpoint.get(
                "previous_signature"
            )
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "ok": False,
                "reason": "invalid_checkpoint_record",
                "checkpoint_index": expected_sequence,
                "detail": str(exc),
            }

        if sequence != expected_sequence:
            return {
                "ok": False,
                "reason": "checkpoint_sequence_gap",
                "checkpoint_sequence": sequence,
                "expected_sequence": expected_sequence,
            }
        if linked_previous != previous_signature:
            return {
                "ok": False,
                "reason": "checkpoint_previous_signature_mismatch",
                "checkpoint_sequence": sequence,
            }
        if event_count < 0 or event_count > len(records):
            return {
                "ok": False,
                "reason": "checkpoint_event_count_out_of_range",
                "checkpoint_sequence": sequence,
                "event_count": event_count,
                "audit_record_count": len(records),
            }

        boundary_hash = (
            records[event_count - 1].get("event_hash")
            if event_count > 0
            else None
        )
        if head_hash != boundary_hash:
            return {
                "ok": False,
                "reason": "checkpoint_audit_boundary_mismatch",
                "checkpoint_sequence": sequence,
                "checkpoint_head_hash": head_hash,
                "audit_boundary_hash": boundary_hash,
            }

        previous_signature = signature

    return {
        "ok": True,
        "checked": len(checkpoints),
        "latest_sequence": (
            len(checkpoints)
            if checkpoints
            else None
        ),
        "signature_authenticity": "not_checked",
    }


def _verify_receipt_bindings(
    receipts: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    by_sequence = {
        int(checkpoint["sequence"]): checkpoint
        for checkpoint in checkpoints
    }

    for index, receipt in enumerate(receipts, start=1):
        try:
            sequence = int(receipt["checkpoint_sequence"])
            checkpoint_signature = str(
                receipt["checkpoint_signature"]
            )
            checkpoint_head_hash = receipt.get(
                "checkpoint_head_hash"
            )
            fingerprint = receipt.get(
                "checkpoint_fingerprint"
            )
        except (KeyError, TypeError, ValueError) as exc:
            return {
                "ok": False,
                "reason": "invalid_witness_receipt",
                "receipt_index": index,
                "detail": str(exc),
            }

        checkpoint = by_sequence.get(sequence)
        if checkpoint is None:
            return {
                "ok": False,
                "reason": "witness_receipt_checkpoint_missing",
                "receipt_index": index,
                "checkpoint_sequence": sequence,
            }
        if checkpoint_signature != checkpoint.get("signature"):
            return {
                "ok": False,
                "reason": "witness_receipt_signature_binding_mismatch",
                "receipt_index": index,
                "checkpoint_sequence": sequence,
            }
        if checkpoint_head_hash != checkpoint.get("head_hash"):
            return {
                "ok": False,
                "reason": "witness_receipt_head_binding_mismatch",
                "receipt_index": index,
                "checkpoint_sequence": sequence,
            }

        try:
            checkpoint_obj = __import__(
                "audit_checkpoint"
            ).AuditCheckpoint(**checkpoint)
        except (TypeError, AttributeError) as exc:
            return {
                "ok": False,
                "reason": "invalid_checkpoint_for_fingerprint",
                "checkpoint_sequence": sequence,
                "detail": str(exc),
            }
        expected_fingerprint = checkpoint_fingerprint(
            checkpoint_obj
        )
        if fingerprint != expected_fingerprint:
            return {
                "ok": False,
                "reason": "witness_receipt_fingerprint_binding_mismatch",
                "receipt_index": index,
                "checkpoint_sequence": sequence,
            }

    return {
        "ok": True,
        "checked": len(receipts),
        "signature_authenticity": "not_checked",
    }


def verify_evidence_bundle(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    if bundle.get("schema") != BUNDLE_SCHEMA:
        return {
            "ok": False,
            "reason": "unsupported_bundle_schema",
            "schema": bundle.get("schema"),
        }

    core = {
        "schema": bundle.get("schema"),
        "audit_records": bundle.get("audit_records"),
        "checkpoints": bundle.get("checkpoints"),
        "witness_receipts": bundle.get(
            "witness_receipts"
        ),
        "snapshot": bundle.get("snapshot"),
    }
    expected_bundle_id = _canonical_hash(core)
    if bundle.get("bundle_id") != expected_bundle_id:
        return {
            "ok": False,
            "reason": "bundle_hash_mismatch",
            "expected_bundle_id": expected_bundle_id,
            "actual_bundle_id": bundle.get("bundle_id"),
        }

    records = bundle.get("audit_records")
    checkpoints = bundle.get("checkpoints")
    receipts = bundle.get("witness_receipts")
    if not isinstance(records, list):
        return {
            "ok": False,
            "reason": "audit_records_must_be_array",
        }
    if not isinstance(checkpoints, list):
        return {
            "ok": False,
            "reason": "checkpoints_must_be_array",
        }
    if not isinstance(receipts, list):
        return {
            "ok": False,
            "reason": "witness_receipts_must_be_array",
        }

    audit = _verify_audit_records(records)
    if not audit["ok"]:
        return {
            "ok": False,
            "reason": "audit_chain_invalid",
            "audit_chain": audit,
        }

    checkpoint = _verify_checkpoint_bindings(
        checkpoints,
        records,
    )
    if not checkpoint["ok"]:
        return {
            "ok": False,
            "reason": "checkpoint_binding_invalid",
            "audit_chain": audit,
            "checkpoints": checkpoint,
        }

    witness = _verify_receipt_bindings(
        receipts,
        checkpoints,
    )
    if not witness["ok"]:
        return {
            "ok": False,
            "reason": "witness_binding_invalid",
            "audit_chain": audit,
            "checkpoints": checkpoint,
            "witness_receipts": witness,
        }

    snapshot = bundle.get("snapshot")
    if not isinstance(snapshot, dict):
        return {
            "ok": False,
            "reason": "snapshot_must_be_object",
        }
    snapshot_audit = snapshot.get("audit_chain")
    if (
        not isinstance(snapshot_audit, dict)
        or snapshot_audit.get("head_hash")
        != audit.get("head_hash")
        or snapshot_audit.get("checked")
        != audit.get("checked")
    ):
        return {
            "ok": False,
            "reason": "snapshot_audit_summary_mismatch",
        }

    return {
        "ok": True,
        "bundle_id": expected_bundle_id,
        "audit_chain": audit,
        "checkpoints": checkpoint,
        "witness_receipts": witness,
        "authenticity": {
            "checkpoint_signatures": "not_checked",
            "witness_receipt_signatures": "not_checked",
        },
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify a HumanQueue evidence bundle offline."
    )
    parser.add_argument(
        "bundle",
        help="Path to a HumanQueue evidence bundle JSON file.",
    )
    args = parser.parse_args()

    path = Path(args.bundle)
    bundle = json.loads(path.read_text(encoding="utf-8"))
    result = verify_evidence_bundle(bundle)
    print(json.dumps(result, sort_keys=True, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
