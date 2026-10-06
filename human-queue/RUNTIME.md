# HumanQueue Runtime — executable E2E

The public page demonstrates the interaction model. This directory now also
contains a deliberately small **real blocking primitive**.

## The contract

```text
machine
  -> ask(...)
  -> durable WAITING_FOR_HUMAN
  -> human decides exactly once
  -> decision is persisted
  -> blocked machine observes it
  -> machine resumes
```

The first implementation is SQLite-backed and standard-library-only. It is not
intended to be the final distributed architecture; it is the smallest artifact
that proves HumanQueue is more than UI.

## Run the proof

Use the web UI plus a producer from the repository root.

Terminal A — start HumanQueue:\n\n```bash\npython human-queue/server.py\n```\n\nOpen `http://127.0.0.1:8765`. The header should switch to **durable runtime connected**.\n\nTerminal B — start a blocked producer:\n\n```bash\npython human-queue/demo_blocked_process.py producer\n```\n\nYou should see:

```text
[agent] WAITING_FOR_HUMAN wait_...
```

The process remains blocked.

The task appears automatically in the browser over **Server-Sent Events** (`GET /api/events`). If the stream disconnects, the UI falls back to polling while the browser reconnects. Click **Approve**. Terminal B then continues by itself:

```text
[agent] RESUMED cleanup-step-3
[agent] deleting keys ... done
[agent] WORKFLOW_COMPLETE
```

That transition is the current Reality Delta.

## Semantics already enforced

- durable SQLite wait records
- idempotent producer submission via `idempotency_key`
- exactly-once decision boundary
- same-decision replay is safe
- conflicting second decisions fail loudly
- explicit `resume_token`
- blocking wait with timeout
- pending queue retrieval

## Next hardening steps

1. replace browser polling with SSE or event delivery\n2. add leases/claims for multiple human reviewers\n3. add webhook/MCP/GitHub resume adapters\n4. add audit signatures and policy provenance\n5. add authentication and actor identity\n6. move from single-node SQLite to an optional distributed store

The architectural rule is simple: **UI is optional; the durable boundary is the
product primitive.**


## Live delivery

The browser now prefers an SSE stream:

```text
producer ask()
    ↓
SQLite wait
    ↓
GET /api/events
    ↓
event: queue
    ↓
browser updates immediately
```

The stream sends a full pending-queue snapshot whenever its durable signature changes.
This keeps the first implementation deliberately simple and deterministic. Browser
polling remains as a resilience fallback if EventSource is unavailable or reconnecting.


## Audit provenance

Every durable boundary now has a transactional audit trail. Events are written
in the same SQLite transaction as the state change they describe.

Current event types:

```text
WAIT_CREATED
CLAIMED
CLAIM_RENEWED
CLAIM_RELEASED
DECISION_COMMITTED
```

Read the history for one wait:

```http
GET /api/waits/{wait_id}/events
```

Or the most recent cross-queue activity:

```http
GET /api/audit
```

The live browser timeline uses this durable provenance instead of inventing a
parallel UI-only history when connected to the runtime. Idempotent decision
replays do not duplicate `DECISION_COMMITTED`, and rejected conflicting
decisions do not append false events.


## Machine acknowledgement protocol

A human decision is not treated as proof that the machine successfully
continued. Approved/edit/resolve decisions now create a distinct resume request,
and the machine reports execution progress back to HumanQueue:

```text
DECISION_COMMITTED
  -> RESUME_REQUESTED
  -> PROCESS_RESUMED
  -> PROCESS_COMPLETED
                 or
     PROCESS_FAILED
```

The runtime exposes:

```python
queue.mark_resumed(wait_id, actor="agent")
queue.mark_completed(wait_id, actor="agent", success=True, detail="done")
```

and equivalent HTTP endpoints:

```http
POST /api/waits/{wait_id}/resumed
POST /api/waits/{wait_id}/complete
```

Rejected decisions never create a resume request. Completion before a resume
acknowledgement is rejected. Resume and same-terminal-result replays are
idempotent, while contradictory terminal outcomes fail loudly.

SSE queue frames now include recent audit events as well as pending waits, so
machine-side `PROCESS_RESUMED`, `PROCESS_COMPLETED`, and `PROCESS_FAILED`
events appear in the browser without polling.


## Resume adapters

The first cross-system adapter is now available in `human-queue/adapters.py`:

```python
from adapters import GenericWebhookAdapter

adapter = GenericWebhookAdapter(
    "https://worker.example/resume",
    bearer_token="...",
)

adapter.dispatch(queue, decided_wait)
```

A successful webhook response records `RESUME_DISPATCHED`, but intentionally
does **not** mark the machine as resumed. The target system must still
acknowledge execution through:

```text
POST /api/waits/{wait_id}/resumed
POST /api/waits/{wait_id}/complete
```

This preserves a strict distinction between:

```text
message delivered
!=
machine resumed
!=
machine completed
```

Webhook audit provenance strips URL credentials, query strings, fragments, and
bearer tokens so secrets are not written into the durable event log.
