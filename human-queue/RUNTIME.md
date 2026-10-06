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


### GitHub Actions / repository_dispatch

HumanQueue can also resume a GitHub-hosted workflow without custom glue:

```python
from adapters import GitHubRepositoryDispatchAdapter

adapter = GitHubRepositoryDispatchAdapter(
    "owner/repo",
    token=os.environ["GITHUB_TOKEN"],
    event_type="humanqueue-resume",
)

adapter.dispatch(queue, decided_wait)
```

The adapter calls GitHub's `repository_dispatch` endpoint with the wait ID,
resume token, URI, source, and committed human decision. Audit provenance stores
only:

```text
github://owner/repo/humanqueue-resume
```

and never persists the GitHub token.

As with every adapter, dispatch success means delivery only. The resumed GitHub
workflow should acknowledge actual execution through the HumanQueue
`/resumed` and `/complete` endpoints.


## Reliable resume delivery

All resume adapters can now share a common delivery contract:

```python
from adapters import RetryPolicy, dispatch_with_retry

dispatch_with_retry(
    queue,
    decided_wait,
    adapter,
    policy=RetryPolicy(
        max_attempts=3,
        base_delay=0.25,
        multiplier=2,
        max_delay=5,
    ),
)
```

Delivery provenance is explicit:

```text
RESUME_DELIVERY_ATTEMPT
RESUME_DELIVERY_FAILED
RESUME_DELIVERY_ATTEMPT
RESUME_DISPATCHED
```

If every attempt fails:

```text
RESUME_DELIVERY_ATTEMPT
RESUME_DELIVERY_FAILED
...
RESUME_DEAD_LETTERED
```

Retries use bounded exponential backoff. The retry wrapper is synchronous in
this MVP; durable scheduled retries/workers are a later deployment concern.
The important semantic boundary is already preserved: a dead-lettered resume
request remains distinct from machine execution state and never becomes
`PROCESS_RESUMED` by implication.


## Durable delivery worker

Resume delivery can now survive process restarts. Delivery jobs are persisted in
the same SQLite database with:

```text
status
attempt
max_attempts
next_attempt_at
claimed_by
claim_expires_at
last_error
```

Create a durable delivery after a committed decision:

```http
POST /api/waits/{wait_id}/delivery
Content-Type: application/json

{
  "adapter": "webhook",
  "target": "https://worker.example/resume",
  "max_attempts": 4,
  "base_delay": 1,
  "multiplier": 2,
  "max_delay": 8
}
```

Inspect persisted jobs:

```http
GET /api/deliveries
```

Run a worker:

```bash
HUMANQUEUE_WEBHOOK_URL=https://worker.example/resume \
python human-queue/delivery_worker.py
```

or for GitHub:

```bash
HUMANQUEUE_GITHUB_REPOSITORY=owner/repo \
HUMANQUEUE_GITHUB_TOKEN=... \
python human-queue/delivery_worker.py
```

Adapter credentials stay in the worker process environment. SQLite persists only
the adapter name, logical target, scheduling metadata, and delivery state.

Workers claim one due job with a bounded lease. If a worker crashes, another
worker can take over after lease expiry. Failed attempts persist
`next_attempt_at`, so restarting the worker or the server does not reset the
retry budget.

Network delivery is deliberately at-least-once. Webhook requests include a
stable `Idempotency-Key`, and GitHub repository-dispatch payloads include a
stable `delivery_key`, allowing receivers to deduplicate the crash window
between successful remote delivery and local `dispatched` persistence.


## Resume bindings and automatic delivery materialization

A wait can now declare where its committed decision should be delivered:

```json
{
  "uri": "human://approve",
  "title": "Deploy release?",
  "source": "ci",
  "resume_token": "deploy-step",
  "resume_binding": {
    "adapter": "github_repository_dispatch",
    "target": "github://owner/repo/humanqueue-resume",
    "max_attempts": 4,
    "base_delay": 1,
    "multiplier": 2,
    "max_delay": 8
  }
}
```

For non-reject decisions, HumanQueue automatically materializes one durable
delivery job and records `RESUME_DELIVERY_QUEUED`. Decision replay is safe:
the delivery queue is unique by `(wait_id, adapter, target)`, and the queued
audit event is idempotent.

Rejected decisions never materialize a delivery.

Resume bindings are validated before wait creation through the HTTP API, so an
invalid target cannot be discovered only after a human has already approved.

### Crash-window reconciliation

Decision persistence and delivery enqueue are separate durable operations, so a
process could theoretically crash after `RESUME_REQUESTED` but before the
delivery row is written.

The delivery worker closes that window by reconciling every persisted
`resume_requested` wait with a `resume_binding` before it claims due jobs.
Missing jobs are recreated idempotently. This means a restart can recover:

```text
DECISION_COMMITTED
RESUME_REQUESTED
<process crash>
restart
reconciler
RESUME_DELIVERY_QUEUED
worker claim
...
```


## Named resume destinations

Agents no longer need to carry raw callback URLs or repository targets in every
wait. HumanQueue can register secret-free logical destinations:

```http
POST /api/destinations
Content-Type: application/json

{
  "name": "prod-deploy",
  "adapter": "webhook",
  "target": "https://worker.example/resume",
  "max_attempts": 4,
  "base_delay": 1,
  "multiplier": 2,
  "max_delay": 8
}
```

Then a wait only references the logical name:

```json
{
  "resume_binding": {
    "destination": "prod-deploy"
  }
}
```

List configured destinations:

```http
GET /api/destinations
```

At decision time HumanQueue resolves the destination again. If it was disabled
after the wait was created, a non-reject decision fails closed before the human
decision is committed.

Once a decision is accepted, the resolved adapter, target, and retry policy are
snapshotted into the durable delivery job. Later destination edits therefore do
not rewrite the meaning of an already-approved execution.

Webhook destination URLs are sanitized before persistence: credentials, query
parameters, and fragments are stripped. Adapter credentials remain outside the
registry and continue to live only in the worker environment.

Raw `adapter + target` resume bindings remain supported for backward
compatibility, but named destinations are the preferred control-plane path.


## Destination revisions and configuration provenance

Named destinations are now versioned. Each material change to adapter, target,
retry policy, or enabled state creates a monotonically increasing revision:

```text
prod-deploy rev 1
  target = /v1

prod-deploy rev 2
  target = /v2

prod-deploy rev 3
  enabled = false
```

Writing an identical configuration again does not create a synthetic revision.

Inspect history:

```http
GET /api/destinations/{name}/history
```

When a named destination is resolved for an approved wait, HumanQueue snapshots:

```text
destination
destination_revision
adapter
target
retry policy
```

into the durable delivery row. The same destination revision is also recorded
in the `RESUME_DELIVERY_QUEUED` audit event.

This makes the provenance chain explicit:

```text
human decision
→ prod-deploy revision 7
→ immutable delivery snapshot
→ delivery attempts
→ machine acknowledgement
```

Later edits to `prod-deploy` create a new revision and do not rewrite already
approved deliveries or their audit history.


## Actor and policy provenance

Destination revisions now record who changed them and why:

```json
{
  "name": "prod-deploy",
  "actor": "release-admin",
  "reason": "CAB-42",
  "allowed_decision_actors": ["alice", "bob"]
}
```

A material destination change records `changed_by` and `change_reason` on the
new revision. Repeating an identical configuration is a no-op: it does not
create a fake revision, change `updated_at`, or overwrite the original
provenance.

The resolved revision snapshots these fields into the durable delivery:

```text
destination = prod-deploy
destination_revision = 7
destination_changed_by = release-admin
destination_change_reason = CAB-42
```

and into `RESUME_DELIVERY_QUEUED`, so destination history, delivery rows, and
wait audit events can be cross-checked.

### Logical decision actor policy

A destination may specify a logical allowlist:

```json
{
  "allowed_decision_actors": ["alice", "bob"]
}
```

For non-reject decisions, HumanQueue checks this policy before committing the
decision. An unauthorized actor receives HTTP 403, the wait remains waiting,
and no `DECISION_COMMITTED` event is written. The denied attempt is instead
recorded as `DECISION_DENIED` with the destination revision and policy
context.

Reject remains available as a safe exit even for actors outside the continuation
allowlist because it does not cause machine execution.

Important: actor strings are logical identities in this local MVP. They are not
cryptographically authenticated principals yet. Production authorization still
requires an authentication layer that binds requests to trustworthy identities.


## Optional authenticated actor binding

HumanQueue can now bind bearer tokens to logical human actors without storing
those credentials in SQLite.

Configure the runtime:

```bash
export HUMANQUEUE_ACTOR_TOKENS='{
  "alice": "replace-with-secret-token-a",
  "bob": "replace-with-secret-token-b"
}'
python human-queue/server.py
```

Then human control-plane mutations use:

```http
Authorization: Bearer replace-with-secret-token-a
```

When authentication is enabled, the runtime derives the actor from the bearer
token for:

```text
destination create/update
wait claim
wait release
human decision
```

A missing or invalid token returns HTTP 401. If the request body claims a
different actor than the authenticated token, the request returns HTTP 403
`actor_mismatch`; the body cannot impersonate another logical actor.

This composes with destination decision policy:

```text
Bearer token
  -> authenticated actor = alice
  -> prod-deploy rev 7 allowed_decision_actors
  -> decision allowed / denied
  -> auditable actor on DECISION_COMMITTED or DECISION_DENIED
```

The token map is process configuration only and is never persisted to the
HumanQueue database or audit log.

This is intentionally a lightweight local authentication layer, not a full IAM
system. Production deployments should replace or front it with an identity
provider / gateway that supplies trustworthy principals, rotation, revocation,
and stronger credential lifecycle management.
