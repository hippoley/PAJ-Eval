import importlib.util
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


destinations = load("human_queue_destinations", ROOT / "destinations.py")
DestinationRegistry = destinations.DestinationRegistry
RetryPolicy = destinations.RetryPolicy
resolve_resume_binding = destinations.resolve_resume_binding


def test_destination_registry_persists_and_updates_without_secrets(tmp_path):
    db = tmp_path / "queue.db"
    registry = DestinationRegistry(db)

    first = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        policy=RetryPolicy(max_attempts=4, base_delay=1, multiplier=2, max_delay=8),
        now=100,
    )
    assert first.name == "prod-deploy"
    assert first.enabled is True
    assert first.created_at == 100

    reopened = DestinationRegistry(db)
    loaded = reopened.get("prod-deploy", require_enabled=True)
    assert loaded.target == "https://worker.example/resume"
    assert loaded.policy.max_attempts == 4

    updated = reopened.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v2",
        policy=RetryPolicy(max_attempts=5),
        now=200,
    )
    assert updated.created_at == 100
    assert updated.updated_at == 200
    assert updated.target.endswith("/v2")
    assert [item.name for item in reopened.list()] == ["prod-deploy"]


def test_disabled_destination_fails_closed(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
    )
    registry.set_enabled("prod-deploy", False)

    try:
        registry.get("prod-deploy", require_enabled=True)
    except RuntimeError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError("disabled destination unexpectedly resolved")


def test_named_binding_resolves_to_immutable_snapshot(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    registry.put(
        "github-release",
        adapter="github_repository_dispatch",
        target="github://acme/app/humanqueue-resume",
        policy=RetryPolicy(max_attempts=4, base_delay=1, multiplier=2, max_delay=8),
    )

    snapshot = resolve_resume_binding(
        {"destination": "github-release"},
        registry,
    )
    assert snapshot["destination"] == "github-release"
    assert snapshot["destination_revision"] == 1
    assert snapshot["adapter"] == "github_repository_dispatch"
    assert snapshot["target"] == "github://acme/app/humanqueue-resume"
    assert snapshot["max_attempts"] == 4
    assert snapshot["base_delay"] == 1.0
    assert snapshot["multiplier"] == 2.0
    assert snapshot["max_delay"] == 8.0

    registry.put(
        "github-release",
        adapter="github_repository_dispatch",
        target="github://acme/app/new-event",
    )
    assert snapshot["target"] == "github://acme/app/humanqueue-resume"


def test_raw_binding_remains_backward_compatible(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    snapshot = resolve_resume_binding(
        {
            "adapter": "webhook",
            "target": "https://worker.example/resume",
            "max_attempts": 2,
        },
        registry,
    )
    assert snapshot["adapter"] == "webhook"
    assert snapshot["target"] == "https://worker.example/resume"
    assert snapshot["max_attempts"] == 2


def test_webhook_destination_strips_url_secrets_before_persisting(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    item = registry.put(
        "secret-free",
        adapter="webhook",
        target="https://user:pass@example.com:8443/resume?token=secret#frag",
    )

    assert item.target == "https://example.com:8443/resume"
    reopened = DestinationRegistry(tmp_path / "queue.db")
    assert reopened.get("secret-free").target == "https://example.com:8443/resume"


def test_destination_revision_only_changes_when_configuration_changes(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")

    first = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v1",
        policy=RetryPolicy(max_attempts=4),
        now=100,
    )
    same = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v1",
        policy=RetryPolicy(max_attempts=4),
        now=110,
    )
    changed = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v2",
        policy=RetryPolicy(max_attempts=4),
        now=120,
    )

    assert first.revision == 1
    assert same.revision == 1
    assert changed.revision == 2
    assert [item.revision for item in registry.history("prod-deploy")] == [1, 2]
    assert [item.target for item in registry.history("prod-deploy")] == [
        "https://worker.example/v1",
        "https://worker.example/v2",
    ]


def test_enable_disable_changes_destination_revision(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    created = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        now=100,
    )
    disabled = registry.set_enabled("prod-deploy", False, now=110)
    enabled = registry.set_enabled("prod-deploy", True, now=120)

    assert created.revision == 1
    assert disabled.revision == 2
    assert enabled.revision == 3
    assert [item.enabled for item in registry.history("prod-deploy")] == [
        True,
        False,
        True,
    ]


def test_named_binding_snapshot_contains_destination_revision(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    registry.put(
        "github-release",
        adapter="github_repository_dispatch",
        target="github://acme/app/humanqueue-resume",
    )
    snapshot = resolve_resume_binding(
        {"destination": "github-release"},
        registry,
    )

    assert snapshot["destination"] == "github-release"
    assert snapshot["destination_revision"] == 1


def test_destination_history_records_actor_and_reason(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")

    first = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v1",
        actor="alice",
        reason="initial production rollout",
        now=100,
    )
    second = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/v2",
        actor="bob",
        reason="migrate resume endpoint",
        now=200,
    )

    assert first.changed_by == "alice"
    assert first.change_reason == "initial production rollout"
    assert second.revision == 2
    assert second.changed_by == "bob"
    assert second.change_reason == "migrate resume endpoint"

    history = registry.history("prod-deploy")
    assert [(h.revision, h.changed_by, h.change_reason) for h in history] == [
        (1, "alice", "initial production rollout"),
        (2, "bob", "migrate resume endpoint"),
    ]


def test_identical_destination_write_preserves_original_provenance(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    first = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        actor="alice",
        reason="approved setup",
        now=100,
    )
    replay = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        actor="mallory",
        reason="should not rewrite provenance",
        now=200,
    )

    assert replay.revision == first.revision == 1
    assert replay.updated_at == first.updated_at == 100
    assert replay.changed_by == "alice"
    assert replay.change_reason == "approved setup"
    assert len(registry.history("prod-deploy")) == 1


def test_destination_snapshot_carries_change_provenance(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        actor="release-admin",
        reason="CAB-42",
    )

    snapshot = resolve_resume_binding(
        {"destination": "prod-deploy"},
        registry,
    )
    assert snapshot["destination_revision"] == 1
    assert snapshot["destination_changed_by"] == "release-admin"
    assert snapshot["destination_change_reason"] == "CAB-42"


def test_decision_actor_policy_is_versioned_with_destination(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    first = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        actor="security-admin",
        reason="initial approvers",
        allowed_decision_actors=["alice", "bob", "alice"],
        now=100,
    )
    second = registry.put(
        "prod-deploy",
        adapter="webhook",
        target="https://worker.example/resume",
        actor="security-admin",
        reason="remove bob",
        allowed_decision_actors=["alice"],
        now=200,
    )

    assert first.allowed_decision_actors == ("alice", "bob")
    assert second.revision == 2
    assert second.allowed_decision_actors == ("alice",)

    history = registry.history("prod-deploy")
    assert history[0].allowed_decision_actors == ("alice", "bob")
    assert history[1].allowed_decision_actors == ("alice",)


def test_decision_actor_policy_rejects_string_shape(tmp_path):
    registry = DestinationRegistry(tmp_path / "queue.db")
    try:
        registry.put(
            "prod-deploy",
            adapter="webhook",
            target="https://worker.example/resume",
            allowed_decision_actors="alice",
        )
    except ValueError as exc:
        assert "must be an array" in str(exc)
    else:
        raise AssertionError("string actor policy unexpectedly accepted")
