import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1] / "human-queue"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = load("runtime", ROOT / "runtime.py")
adapters = load("adapters", ROOT / "adapters.py")
delivery = load("human_queue_delivery", ROOT / "delivery.py")

HumanQueue = runtime.HumanQueue
RetryPolicy = adapters.RetryPolicy
DurableDeliveryQueue = delivery.DurableDeliveryQueue
run_delivery_once = delivery.run_delivery_once
reconcile_bound_deliveries = delivery.reconcile_bound_deliveries
DestinationRegistry = delivery.DestinationRegistry


class RecordingAdapter:
    name = "recording"

    def __init__(self, *, fail_times=0):
        self.audit_target = "recording://target"
        self.fail_times = fail_times
        self.calls = 0

    def dispatch(self, queue, item):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("temporary failure")
        queue.mark_resume_dispatched(
            item.id,
            actor=self.name,
            adapter=self.name,
            target=self.audit_target,
        )
        return {"ok": True}


def approved_wait(queue):
    item = queue.ask(
        uri="human://approve",
        title="Resume durable worker?",
        source="agent",
        resume_token="step-durable",
    )
    return queue.decide(item.id, action="approve", actor="alice")


def test_delivery_survives_process_reopen(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    item = approved_wait(q)

    first = DurableDeliveryQueue(db)
    job = first.enqueue(
        item.id,
        adapter="recording",
        target="recording://target",
        policy=RetryPolicy(max_attempts=3, base_delay=1),
        now=100,
    )

    reopened = DurableDeliveryQueue(db)
    persisted = reopened.get(job.id)

    assert persisted.wait_id == item.id
    assert persisted.status == "pending"
    assert persisted.attempt == 0
    assert [d.id for d in reopened.due(now=100)] == [job.id]


def test_expired_worker_lease_can_be_taken_over(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    item = approved_wait(q)
    deliveries = DurableDeliveryQueue(db)
    job = deliveries.enqueue(
        item.id,
        adapter="recording",
        target="recording://target",
        now=100,
    )

    first = deliveries.claim_due(worker="worker-a", lease_seconds=5, now=100)
    assert first.id == job.id
    assert deliveries.claim_due(worker="worker-b", now=104) is None

    taken = deliveries.claim_due(worker="worker-b", lease_seconds=5, now=106)
    assert taken.id == job.id
    assert taken.claimed_by == "worker-b"


def test_worker_persists_retry_schedule_and_recovers_later(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    item = approved_wait(q)
    deliveries = DurableDeliveryQueue(db)
    adapter = RecordingAdapter(fail_times=1)

    job = deliveries.enqueue(
        item.id,
        adapter=adapter.name,
        target=adapter.audit_target,
        policy=RetryPolicy(
            max_attempts=3,
            base_delay=10,
            multiplier=2,
            max_delay=60,
        ),
        now=100,
    )

    failed = run_delivery_once(
        q,
        deliveries,
        {adapter.name: adapter},
        worker="worker-a",
        now=100,
    )
    assert failed.id == job.id
    assert failed.status == "retry"
    assert failed.attempt == 1
    assert failed.next_attempt_at == 110
    assert deliveries.due(now=109) == []

    reopened = DurableDeliveryQueue(db)
    recovered = run_delivery_once(
        q,
        reopened,
        {adapter.name: adapter},
        worker="worker-b",
        now=110,
    )
    assert recovered.status == "dispatched"
    assert recovered.attempt == 2
    assert adapter.calls == 2

    types = [event.event_type for event in q.audit_events(item.id)]
    assert types.count("RESUME_DELIVERY_ATTEMPT") == 2
    assert types.count("RESUME_DELIVERY_FAILED") == 1
    assert types.count("RESUME_DISPATCHED") == 1


def test_worker_dead_letters_after_durable_attempt_budget(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    item = approved_wait(q)
    deliveries = DurableDeliveryQueue(db)
    adapter = RecordingAdapter(fail_times=10)

    job = deliveries.enqueue(
        item.id,
        adapter=adapter.name,
        target=adapter.audit_target,
        policy=RetryPolicy(max_attempts=2, base_delay=5),
        now=100,
    )

    first = run_delivery_once(
        q,
        deliveries,
        {adapter.name: adapter},
        worker="worker-a",
        now=100,
    )
    assert first.status == "retry"
    assert first.next_attempt_at == 105

    second = run_delivery_once(
        q,
        DurableDeliveryQueue(db),
        {adapter.name: adapter},
        worker="worker-b",
        now=105,
    )
    assert second.status == "dead_letter"
    assert second.attempt == 2
    assert DurableDeliveryQueue(db).due(now=999) == []

    events = q.audit_events(item.id)
    dead = [e for e in events if e.event_type == "RESUME_DEAD_LETTERED"]
    assert len(dead) == 1
    assert dead[0].data["attempt"] == 2


def test_enqueue_is_idempotent_for_same_wait_adapter_and_target(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    item = approved_wait(q)
    deliveries = DurableDeliveryQueue(db)

    first = deliveries.enqueue(
        item.id,
        adapter="recording",
        target="recording://target",
        now=100,
    )
    second = deliveries.enqueue(
        item.id,
        adapter="recording",
        target="recording://target",
        now=101,
    )

    assert first.id == second.id


def test_missing_adapter_is_retryable_and_then_dead_lettered(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    item = approved_wait(q)
    deliveries = DurableDeliveryQueue(db)
    deliveries.enqueue(
        item.id,
        adapter="missing",
        target="missing://target",
        policy=RetryPolicy(max_attempts=2, base_delay=1),
        now=100,
    )

    first = run_delivery_once(
        q,
        deliveries,
        {},
        worker="worker-a",
        now=100,
    )
    assert first.status == "retry"

    second = run_delivery_once(
        q,
        DurableDeliveryQueue(db),
        {},
        worker="worker-b",
        now=101,
    )
    assert second.status == "dead_letter"
    assert "adapter not registered" in second.last_error


def test_reconciler_materializes_delivery_after_crash_window(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    item = q.ask(
        uri="human://approve",
        title="Recover binding?",
        source="agent",
        resume_token="step-reconcile",
        resume_binding={
            "adapter": "recording",
            "target": "recording://target",
            "max_attempts": 4,
            "base_delay": 2,
            "multiplier": 2,
            "max_delay": 10,
        },
    )
    q.decide(item.id, action="approve", actor="alice")

    deliveries = DurableDeliveryQueue(db)
    assert deliveries.list() == []

    created = reconcile_bound_deliveries(q, deliveries)
    assert len(created) == 1
    job = created[0]
    assert job.wait_id == item.id
    assert job.status == "pending"
    assert job.max_attempts == 4
    assert job.base_delay == 2

    again = reconcile_bound_deliveries(q, DurableDeliveryQueue(db))
    assert len(again) == 1
    assert again[0].id == job.id
    assert len(DurableDeliveryQueue(db).list()) == 1

    events = q.audit_events(item.id)
    queued = [e for e in events if e.event_type == "RESUME_DELIVERY_QUEUED"]
    assert len(queued) == 1
    assert queued[0].data["delivery_id"] == job.id


def test_reconciler_ignores_rejected_bound_wait(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    item = q.ask(
        uri="human://approve",
        title="Do not materialize",
        source="agent",
        resume_binding={
            "adapter": "recording",
            "target": "recording://target",
        },
    )
    q.decide(item.id, action="reject", actor="alice")

    deliveries = DurableDeliveryQueue(db)
    assert reconcile_bound_deliveries(q, deliveries) == []
    assert deliveries.list() == []


def test_reconciler_resolves_named_destination_after_restart(tmp_path):
    db = tmp_path / "queue.db"
    q = HumanQueue(db)
    destinations = DestinationRegistry(db)
    destinations.put(
        "prod-deploy",
        adapter="recording",
        target="recording://prod",
        policy=RetryPolicy(max_attempts=5, base_delay=3, multiplier=2, max_delay=12),
    )
    item = q.ask(
        uri="human://approve",
        title="Named destination?",
        source="agent",
        resume_token="named-step",
        resume_binding={"destination": "prod-deploy"},
    )
    q.decide(item.id, action="approve", actor="alice")

    deliveries = DurableDeliveryQueue(db)
    created = reconcile_bound_deliveries(q, deliveries, destinations)

    assert len(created) == 1
    job = created[0]
    assert job.adapter == "recording"
    assert job.target == "recording://prod"
    assert job.max_attempts == 5
    assert job.base_delay == 3
