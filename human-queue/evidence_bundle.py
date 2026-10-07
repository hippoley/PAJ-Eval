"""Export and offline verification for HumanQueue evidence bundles."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from audit_checkpoint import (
    AuditCheckpoint,
    AuditCheckpointSigner,
    CheckpointSignatureProvider,
    HmacCheckpointSignatureProvider,
    checkpoint_signature_payload,
)
from audit_witness import (
    CheckpointWitnessProvider,
    WitnessReceipt,
    WitnessReceiptJournal,
    WitnessReceiptVerifier,
    HmacWitnessReceiptVerifier,
    checkpoint_fingerprint,
    load_witness_provider,
    load_witness_receipt_journal,
)
from evidence import build_evidence_snapshot
from audit_witness_quorum import WitnessQuorum, load_witness_quorum
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
    witness_provider: CheckpointWitnessProvider | None = None,
    witness_receipts: WitnessReceiptJournal | None = None,
    witness_quorum: WitnessQuorum | None = None,
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
        witness_provider=witness_provider,
        witness_receipts=witness_receipts,
        witness_quorum=witness_quorum,
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
    *,
    signature_provider: CheckpointSignatureProvider | None = None,
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

        if signature_provider is not None:
            checkpoint_obj = AuditCheckpoint(**checkpoint)
            try:
                valid_signature = signature_provider.verify(
                    checkpoint_signature_payload(checkpoint_obj),
                    key_id=checkpoint_obj.key_id,
                    signature=checkpoint_obj.signature,
                )
            except KeyError:
                return {
                    "ok": False,
                    "reason": "checkpoint_signature_key_unknown",
                    "checkpoint_sequence": sequence,
                    "key_id": checkpoint_obj.key_id,
                }
            if not valid_signature:
                return {
                    "ok": False,
                    "reason": "checkpoint_signature_invalid",
                    "checkpoint_sequence": sequence,
                    "key_id": checkpoint_obj.key_id,
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
        "signature_authenticity": (
            "verified"
            if signature_provider is not None
            else "not_checked"
        ),
    }


def _verify_receipt_bindings(
    receipts: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
    *,
    verifiers: dict[str, WitnessReceiptVerifier] | None = None,
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
            checkpoint_obj = AuditCheckpoint(**checkpoint)
        except TypeError as exc:
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

        if verifiers is not None:
            witness = str(receipt.get("witness") or "")
            verifier = verifiers.get(witness)
            if verifier is None:
                return {
                    "ok": False,
                    "reason": "witness_receipt_verifier_missing",
                    "receipt_index": index,
                    "witness": witness,
                }
            try:
                receipt_obj = WitnessReceipt(**receipt)
                valid_receipt = verifier.verify(receipt_obj)
            except (KeyError, TypeError):
                valid_receipt = False
            if not valid_receipt:
                return {
                    "ok": False,
                    "reason": "witness_receipt_signature_invalid",
                    "receipt_index": index,
                    "witness": witness,
                }

    return {
        "ok": True,
        "checked": len(receipts),
        "signature_authenticity": (
            "verified"
            if verifiers is not None
            else "not_checked"
        ),
    }


def verify_evidence_bundle(
    bundle: dict[str, Any],
    *,
    checkpoint_signature_provider: CheckpointSignatureProvider | None = None,
    witness_receipt_verifiers: dict[str, WitnessReceiptVerifier] | None = None,
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
        signature_provider=checkpoint_signature_provider,
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
        verifiers=witness_receipt_verifiers,
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

    snapshot_for_hash = dict(snapshot)
    actual_evidence_id = snapshot_for_hash.pop(
        "evidence_id",
        None,
    )
    expected_evidence_id = _canonical_hash(
        snapshot_for_hash
    )
    if actual_evidence_id != expected_evidence_id:
        return {
            "ok": False,
            "reason": "snapshot_evidence_id_mismatch",
            "expected_evidence_id": expected_evidence_id,
            "actual_evidence_id": actual_evidence_id,
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
            "checkpoint_signatures": checkpoint[
                "signature_authenticity"
            ],
            "witness_receipt_signatures": witness[
                "signature_authenticity"
            ],
        },
    }


def _strict_verifiers_from_env(
    bundle: dict[str, Any],
) -> tuple[
    CheckpointSignatureProvider | None,
    dict[str, WitnessReceiptVerifier] | None,
]:
    checkpoint_provider: CheckpointSignatureProvider | None = None
    raw_checkpoint_keys = os.environ.get(
        "HUMANQUEUE_AUDIT_CHECKPOINT_KEYS",
        "",
    ).strip()
    legacy_checkpoint_key = os.environ.get(
        "HUMANQUEUE_AUDIT_CHECKPOINT_KEY",
        "",
    )

    if raw_checkpoint_keys:
        try:
            parsed = json.loads(raw_checkpoint_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "HUMANQUEUE_AUDIT_CHECKPOINT_KEYS must contain a JSON object"
            ) from exc
        if not isinstance(parsed, dict) or not parsed:
            raise ValueError(
                "HUMANQUEUE_AUDIT_CHECKPOINT_KEYS must contain a non-empty JSON object"
            )
        keys = {
            str(k): str(v)
            for k, v in parsed.items()
        }
        active = os.environ.get(
            "HUMANQUEUE_AUDIT_CHECKPOINT_SIGNING_KEY_ID",
            "",
        ).strip() or sorted(keys)[0]
        checkpoint_provider = HmacCheckpointSignatureProvider(
            keys,
            active,
        )
    elif legacy_checkpoint_key:
        key_id = os.environ.get(
            "HUMANQUEUE_AUDIT_CHECKPOINT_KEY_ID",
            "default",
        ).strip() or "default"
        checkpoint_provider = HmacCheckpointSignatureProvider(
            {key_id: legacy_checkpoint_key},
            key_id,
        )

    witness_verifiers: dict[str, WitnessReceiptVerifier] = {}
    raw_quorum = os.environ.get(
        "HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON",
        "",
    ).strip()
    if raw_quorum:
        try:
            config = json.loads(raw_quorum)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON must contain a JSON object"
            ) from exc
        if isinstance(config, dict):
            raw_witnesses = config.get("witnesses")
            if isinstance(raw_witnesses, dict):
                for name, target in raw_witnesses.items():
                    if not isinstance(target, dict):
                        continue
                    raw_keys = target.get("keys")
                    if isinstance(raw_keys, dict) and raw_keys:
                        witness_verifiers[str(name)] = (
                            HmacWitnessReceiptVerifier(
                                {
                                    str(k): str(v)
                                    for k, v in raw_keys.items()
                                }
                            )
                        )

    if not witness_verifiers:
        raw_witness_keys = os.environ.get(
            "HUMANQUEUE_AUDIT_WITNESS_KEYS",
            "",
        ).strip()
        if raw_witness_keys:
            try:
                parsed = json.loads(raw_witness_keys)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "HUMANQUEUE_AUDIT_WITNESS_KEYS must contain a JSON object"
                ) from exc
            if not isinstance(parsed, dict) or not parsed:
                raise ValueError(
                    "HUMANQUEUE_AUDIT_WITNESS_KEYS must contain a non-empty JSON object"
                )
            verifier = HmacWitnessReceiptVerifier(
                {
                    str(k): str(v)
                    for k, v in parsed.items()
                }
            )
            witness_names = {
                str(receipt.get("witness") or "")
                for receipt in bundle.get("witness_receipts", [])
                if isinstance(receipt, dict)
                and str(receipt.get("witness") or "")
            }
            witness_verifiers = {
                name: verifier
                for name in witness_names
            }

    return (
        checkpoint_provider,
        witness_verifiers or None,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Export or verify HumanQueue provenance evidence bundles."
        )
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    export_parser = subparsers.add_parser(
        "export",
        help="Export an evidence bundle from a HumanQueue database.",
    )
    export_parser.add_argument(
        "--db",
        default=os.environ.get(
            "HUMANQUEUE_DB",
            str(
                Path(__file__).resolve().parent
                / "demo-human-queue.db"
            ),
        ),
        help="HumanQueue SQLite database path.",
    )
    export_parser.add_argument(
        "--output",
        required=True,
        help="Destination JSON file.",
    )

    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify an evidence bundle without opening the HumanQueue database.",
    )
    verify_parser.add_argument(
        "bundle",
        help="Path to a HumanQueue evidence bundle JSON file.",
    )
    verify_parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Also verify checkpoint and witness HMAC signatures "
            "using keyrings from environment variables."
        ),
    )

    args = parser.parse_args()

    if args.command == "export":
        queue = HumanQueue(args.db)
        checkpoint_signer = AuditCheckpointSigner.from_env(
            queue
        )
        witness_provider = load_witness_provider()
        witness_receipts = load_witness_receipt_journal()
        witness_quorum = load_witness_quorum()

        bundle = export_evidence_bundle(
            queue,
            checkpoint_signer=checkpoint_signer,
            witness_provider=witness_provider,
            witness_receipts=witness_receipts,
            witness_quorum=witness_quorum,
        )
        output = Path(args.output)
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            json.dumps(
                bundle,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "bundle_id": bundle["bundle_id"],
                    "output": str(output),
                },
                sort_keys=True,
            )
        )
        return

    path = Path(args.bundle)
    bundle = json.loads(
        path.read_text(encoding="utf-8")
    )
    checkpoint_provider = None
    witness_verifiers = None
    if args.strict:
        (
            checkpoint_provider,
            witness_verifiers,
        ) = _strict_verifiers_from_env(bundle)

        if (
            bundle.get("checkpoints")
            and checkpoint_provider is None
        ):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "reason": "checkpoint_verifier_not_configured",
                    },
                    sort_keys=True,
                    indent=2,
                )
            )
            raise SystemExit(1)

        if (
            bundle.get("witness_receipts")
            and witness_verifiers is None
        ):
            print(
                json.dumps(
                    {
                        "ok": False,
                        "reason": "witness_verifiers_not_configured",
                    },
                    sort_keys=True,
                    indent=2,
                )
            )
            raise SystemExit(1)

    result = verify_evidence_bundle(
        bundle,
        checkpoint_signature_provider=checkpoint_provider,
        witness_receipt_verifiers=witness_verifiers,
    )
    print(
        json.dumps(
            result,
            sort_keys=True,
            indent=2,
        )
    )
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
