import copy
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1] / "human-queue"
sys.path.insert(0, str(ROOT))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = load("human_queue_runtime_bundle", ROOT / "runtime.py")
checkpoint_module = load(
    "human_queue_checkpoint_bundle",
    ROOT / "audit_checkpoint.py",
)
witness_module = load(
    "human_queue_witness_bundle",
    ROOT / "audit_witness.py",
)
quorum_module = load(
    "human_queue_quorum_bundle",
    ROOT / "audit_witness_quorum.py",
)
bundle_module = load(
    "human_queue_evidence_bundle",
    ROOT / "evidence_bundle.py",
)

HumanQueue = runtime.HumanQueue
AuditCheckpointSigner = checkpoint_module.AuditCheckpointSigner
InMemoryWitnessProvider = witness_module.InMemoryWitnessProvider
WitnessReceiptJournal = witness_module.WitnessReceiptJournal
WitnessQuorum = quorum_module.WitnessQuorum
export_evidence_bundle = bundle_module.export_evidence_bundle
verify_evidence_bundle = bundle_module.verify_evidence_bundle


def make_bundle(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Offline evidence bundle",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")

    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    checkpoint = signer.create(now=100)

    witness_a = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    witness_b = InMemoryWitnessProvider(
        witness="witness-b",
        key="secret-b",
    )
    quorum = WitnessQuorum(
        {
            "witness-a": witness_a,
            "witness-b": witness_b,
        },
        threshold=2,
    )
    journal = WitnessReceiptJournal(
        tmp_path / "receipts.jsonl"
    )
    result = quorum.publish(checkpoint)
    for receipt in result.receipts:
        journal.append(
            receipt,
            provider=quorum.provider_for(receipt.witness),
            already_verified=True,
        )

    bundle = export_evidence_bundle(
        queue,
        checkpoint_signer=signer,
        witness_receipts=journal,
        witness_quorum=quorum,
        exported_at=500,
    )
    return bundle


def recalc_bundle_id(bundle):
    core = {
        "schema": bundle["schema"],
        "audit_records": bundle["audit_records"],
        "checkpoints": bundle["checkpoints"],
        "witness_receipts": bundle["witness_receipts"],
        "snapshot": bundle["snapshot"],
    }
    bundle["bundle_id"] = bundle_module._canonical_hash(core)


def recalc_snapshot_id(bundle):
    snapshot = bundle["snapshot"]
    raw = dict(snapshot)
    raw.pop("evidence_id", None)
    snapshot["evidence_id"] = bundle_module._canonical_hash(raw)


def test_bundle_verifies_without_live_database_access(tmp_path):
    bundle = make_bundle(tmp_path)

    result = verify_evidence_bundle(bundle)

    assert result["ok"] is True
    assert result["audit_chain"]["ok"] is True
    assert result["checkpoints"]["ok"] is True
    assert result["witness_receipts"]["ok"] is True
    assert result["authenticity"] == {
        "checkpoint_signatures": "not_checked",
        "witness_receipt_signatures": "not_checked",
    }
    assert bundle["snapshot"]["policy_ok"] is True
    assert bundle["exported_at"] == 500


def test_bundle_id_is_stable_across_export_time(tmp_path):
    first = make_bundle(tmp_path / "first")
    second_core = copy.deepcopy(first)
    second_core["exported_at"] = 999

    assert (
        verify_evidence_bundle(first)["bundle_id"]
        == verify_evidence_bundle(second_core)["bundle_id"]
    )


def test_bundle_detects_audit_data_tamper_even_if_outer_hash_is_recomputed(tmp_path):
    bundle = make_bundle(tmp_path)
    tampered = copy.deepcopy(bundle)
    tampered["audit_records"][0]["data_json"] = '{"forged": true}'
    recalc_bundle_id(tampered)

    result = verify_evidence_bundle(tampered)

    assert result["ok"] is False
    assert result["reason"] == "audit_chain_invalid"
    assert result["audit_chain"]["reason"] == "audit_event_hash_mismatch"


def test_bundle_detects_checkpoint_boundary_tamper_with_recomputed_outer_hash(tmp_path):
    bundle = make_bundle(tmp_path)
    tampered = copy.deepcopy(bundle)
    tampered["checkpoints"][0]["head_hash"] = "0" * 64
    recalc_bundle_id(tampered)

    result = verify_evidence_bundle(tampered)

    assert result["ok"] is False
    assert result["reason"] == "checkpoint_binding_invalid"
    assert result["checkpoints"]["reason"] == "checkpoint_audit_boundary_mismatch"


def test_bundle_detects_witness_receipt_binding_tamper(tmp_path):
    bundle = make_bundle(tmp_path)
    tampered = copy.deepcopy(bundle)
    tampered["witness_receipts"][0]["checkpoint_fingerprint"] = "0" * 64
    recalc_bundle_id(tampered)

    result = verify_evidence_bundle(tampered)

    assert result["ok"] is False
    assert result["reason"] == "witness_binding_invalid"
    assert result["witness_receipts"]["reason"] == (
        "witness_receipt_fingerprint_binding_mismatch"
    )


def test_bundle_detects_snapshot_summary_tamper_with_recomputed_outer_hash(tmp_path):
    bundle = make_bundle(tmp_path)
    tampered = copy.deepcopy(bundle)
    tampered["snapshot"]["policy_ok"] = False
    recalc_bundle_id(tampered)

    result = verify_evidence_bundle(tampered)

    assert result["ok"] is False
    assert result["reason"] == "snapshot_evidence_id_mismatch"


def test_bundle_detects_outer_bundle_tamper_immediately(tmp_path):
    bundle = make_bundle(tmp_path)
    tampered = copy.deepcopy(bundle)
    tampered["witness_receipts"][0]["witness"] = "mallory"

    result = verify_evidence_bundle(tampered)

    assert result["ok"] is False
    assert result["reason"] == "bundle_hash_mismatch"


def test_bundle_json_round_trip_preserves_verifiability(tmp_path):
    bundle = make_bundle(tmp_path)
    path = tmp_path / "bundle.json"
    path.write_text(
        json.dumps(bundle, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    loaded = json.loads(path.read_text(encoding="utf-8"))

    result = verify_evidence_bundle(loaded)

    assert result["ok"] is True
    assert result["bundle_id"] == bundle["bundle_id"]
