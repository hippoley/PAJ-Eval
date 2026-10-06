import importlib.util
import sys
from dataclasses import replace
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


runtime = load("human_queue_runtime_witness_quorum", ROOT / "runtime.py")
checkpoint_module = load(
    "human_queue_checkpoint_witness_quorum",
    ROOT / "audit_checkpoint.py",
)
witness_module = load(
    "human_queue_witness_quorum_client",
    ROOT / "audit_witness.py",
)
quorum_module = load(
    "human_queue_witness_quorum",
    ROOT / "audit_witness_quorum.py",
)

HumanQueue = runtime.HumanQueue
AuditCheckpointSigner = checkpoint_module.AuditCheckpointSigner
InMemoryWitnessProvider = witness_module.InMemoryWitnessProvider
WitnessQuorum = quorum_module.WitnessQuorum


def make_checkpoint(tmp_path):
    queue = HumanQueue(tmp_path / "queue.db")
    item = queue.ask(
        uri="human://approve",
        title="Quorum checkpoint",
        source="agent",
    )
    queue.decide(item.id, action="approve", actor="alice")
    signer = AuditCheckpointSigner(
        queue,
        tmp_path / "checkpoints.jsonl",
        key="checkpoint-secret",
    )
    return signer.create(now=100)


class FailingWitness:
    def publish(self, checkpoint):
        raise RuntimeError("witness unavailable")

    def verify(self, receipt):
        raise RuntimeError("witness unavailable")


def test_two_of_three_witnesses_can_satisfy_quorum(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            ),
            "witness-b": InMemoryWitnessProvider(
                witness="witness-b",
                key="secret-b",
            ),
            "witness-c": FailingWitness(),
        },
        threshold=2,
    )

    result = quorum.publish(checkpoint)

    assert result.satisfied is True
    assert result.confirmed_witnesses == (
        "witness-a",
        "witness-b",
    )
    assert result.missing_required_witnesses == ()
    assert "witness-c" in result.failures
    assert len(result.receipts) == 2


def test_three_of_three_fails_when_one_witness_is_unavailable(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            ),
            "witness-b": InMemoryWitnessProvider(
                witness="witness-b",
                key="secret-b",
            ),
            "witness-c": FailingWitness(),
        },
        threshold=3,
    )

    result = quorum.publish(checkpoint)

    assert result.satisfied is False
    assert len(result.confirmed_witnesses) == 2
    assert result.failures["witness-c"] == "witness unavailable"


def test_required_witness_must_be_present_even_when_threshold_is_met(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    quorum = WitnessQuorum(
        {
            "witness-a": InMemoryWitnessProvider(
                witness="witness-a",
                key="secret-a",
            ),
            "witness-b": InMemoryWitnessProvider(
                witness="witness-b",
                key="secret-b",
            ),
            "security-witness": FailingWitness(),
        },
        threshold=2,
        required_witnesses=["security-witness"],
    )

    result = quorum.publish(checkpoint)

    assert result.satisfied is False
    assert result.confirmed_witnesses == (
        "witness-a",
        "witness-b",
    )
    assert result.missing_required_witnesses == (
        "security-witness",
    )


def test_witness_identity_mismatch_does_not_count_toward_quorum(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    quorum = WitnessQuorum(
        {
            "expected-witness": InMemoryWitnessProvider(
                witness="different-witness",
                key="secret-a",
            ),
        },
        threshold=1,
    )

    result = quorum.publish(checkpoint)

    assert result.satisfied is False
    assert result.confirmed_witnesses == ()
    assert result.failures["expected-witness"].startswith(
        "witness_identity_mismatch:"
    )


def test_duplicate_receipts_from_one_witness_only_count_once(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    witness_a = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    witness_b = InMemoryWitnessProvider(
        witness="witness-b",
        key="secret-b",
    )
    receipt_a = witness_a.publish(checkpoint)

    quorum = WitnessQuorum(
        {
            "witness-a": witness_a,
            "witness-b": witness_b,
        },
        threshold=2,
    )

    result = quorum.evaluate(
        checkpoint,
        [receipt_a, receipt_a],
    )

    assert result.satisfied is False
    assert result.confirmed_witnesses == ("witness-a",)
    assert result.failures["witness-a"] == "duplicate_witness_receipt"


def test_evaluate_rejects_receipt_bound_to_different_checkpoint(tmp_path):
    checkpoint = make_checkpoint(tmp_path)
    witness = InMemoryWitnessProvider(
        witness="witness-a",
        key="secret-a",
    )
    receipt = witness.publish(checkpoint)
    forged = replace(
        receipt,
        checkpoint_head_hash="0" * 64,
    )
    quorum = WitnessQuorum(
        {"witness-a": witness},
        threshold=1,
    )

    result = quorum.evaluate(
        checkpoint,
        [forged],
    )

    assert result.satisfied is False
    assert result.confirmed_witnesses == ()
    assert result.failures["witness-a"] == (
        "checkpoint_head_hash_mismatch"
    )


def test_quorum_rejects_unknown_required_witness():
    try:
        WitnessQuorum(
            {
                "witness-a": InMemoryWitnessProvider(
                    witness="witness-a",
                    key="secret-a",
                )
            },
            threshold=1,
            required_witnesses=["missing-witness"],
        )
    except ValueError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("unknown required witness accepted")
