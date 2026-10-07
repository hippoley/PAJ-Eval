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

The early hardening items (SSE, reviewer leases, durable adapters, identity,
policy provenance, signed audit checkpoints, and external witnesses) are now
implemented in this branch. Remaining production-oriented work is narrower:

1. provide production KMS/HSM or asymmetric checkpoint/witness providers
2. support a distributed durable store without weakening exactly-once decision semantics
3. add operational rotation/runbooks for external identity and witness infrastructure
4. add retention/export policy for large audit histories and evidence bundles
5. continue adversarial/recovery testing across multi-node failure modes

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


## Authenticated machine callbacks

Machine execution acknowledgements can now use a separate bearer-token trust
domain from human operators.

Configure machine principals:

```bash
export HUMANQUEUE_MACHINE_TOKENS='{
  "worker-a": "replace-with-machine-token-a",
  "worker-b": "replace-with-machine-token-b"
}'
```

Then callbacks use:

```http
Authorization: Bearer replace-with-machine-token-a

POST /api/waits/{wait_id}/resumed
POST /api/waits/{wait_id}/complete
```

When machine authentication is configured, the runtime derives the callback
actor from the machine bearer token. Missing or invalid credentials return
HTTP 401. A body that claims a different machine actor returns HTTP 403
`machine_actor_mismatch`.

Human and machine token domains are configured separately and must not reuse
the same credential.

### Destination machine policy

A destination revision may also pin which machine principals may acknowledge an
execution:

```json
{
  "allowed_machine_actors": ["worker-a", "worker-b"]
}
```

The allowlist is snapshotted into the durable delivery at approval time. Later
destination revisions cannot retroactively change the machine authorization
policy for an already-approved execution.

If an authenticated but unauthorized machine calls `/resumed` or
`/complete`, HumanQueue returns HTTP 403 and records
`MACHINE_CALLBACK_DENIED` without changing execution state.

The resulting trust chain is:

```text
authenticated human
→ versioned destination policy
→ immutable delivery snapshot
→ authenticated machine
→ machine actor policy
→ PROCESS_RESUMED / PROCESS_COMPLETED
```

This remains a lightweight local bearer-token implementation. Production
deployments should use stronger workload identity (for example a trusted
gateway, workload identity provider, signed service identity, or mTLS) while
preserving the same HumanQueue actor and policy semantics.


## Pluggable principal providers

Authentication is now separated from HumanQueue policy semantics.

The server authenticates through this logical contract:

```text
HTTP request
  -> AuthContext
       authorization
       headers
       client
  -> AuthProvider
  -> Principal
       actor
       kind       # human | machine
       provider   # bearer-token | trusted-header | future provider
  -> HumanQueue policy / audit
```

The core provider interface is intentionally small:

```python
class AuthProvider(Protocol):
    def authenticate(
        self,
        context: AuthContext,
        *,
        claimed_actor: str | None = None,
    ) -> Principal:
        ...
```

This keeps decision policy, machine policy, durable delivery, and audit
independent from the deployment's identity mechanism.

### Built-in bearer provider

The existing token-map configuration remains backward compatible:

```bash
HUMANQUEUE_ACTOR_TOKENS='{"alice":"..."}'
HUMANQUEUE_MACHINE_TOKENS='{"worker-a":"..."}'
```

When no explicit provider mode is set, these variables automatically select the
`bearer-token` provider.

### Built-in trusted-header provider

HumanQueue can also accept an identity asserted by a trusted reverse proxy or
gateway.

Human example:

```bash
HUMANQUEUE_HUMAN_AUTH_PROVIDER=trusted-header
HUMANQUEUE_HUMAN_PROXY_SECRET='replace-with-shared-proxy-proof'
HUMANQUEUE_HUMAN_ACTOR_HEADER='X-Verified-Human'
```

Machine example:

```bash
HUMANQUEUE_MACHINE_AUTH_PROVIDER=trusted-header
HUMANQUEUE_MACHINE_PROXY_SECRET='replace-with-a-different-proof'
HUMANQUEUE_MACHINE_ACTOR_HEADER='X-Verified-Machine'
```

The default proof header is:

```text
X-HumanQueue-Proxy-Secret
```

A trusted-header request must contain both the configured actor header and the
correct proxy proof. Actor/header claims that disagree with the request body
still fail closed.

Do not expose trusted-header mode directly to untrusted clients. The deployment
must prevent bypassing the authenticating proxy/gateway. Human and machine
built-in provider credentials must also remain disjoint.

### Principal provenance

Execution audit now records only safe identity provenance:

```json
{
  "principal": {
    "kind": "human",
    "provider": "trusted-proxy"
  }
}
```

or:

```json
{
  "principal": {
    "kind": "machine",
    "provider": "bearer-token"
  }
}
```

Raw bearer tokens, trusted proxy proof secrets, request headers, and arbitrary
provider attributes are deliberately not copied into the durable audit log.

The provider boundary is designed so future OIDC/JWT, mTLS, SPIFFE/SPIRE, or
gateway-asserted identity implementations can return the same `Principal`
without changing HumanQueue authorization or execution semantics.


## Signed JWT principal provider (HS256)

HumanQueue now includes a stdlib-only signed JWT provider for deployments that
need expiring, issuer-scoped principals without adding a Python JWT dependency.

This is intentionally **HS256 JWT support**, not full OIDC discovery or JWKS /
RS256 validation.

Human configuration:

```bash
HUMANQUEUE_HUMAN_AUTH_PROVIDER=jwt-hs256
HUMANQUEUE_HUMAN_JWT_KEYS='{
  "current":"replace-with-current-secret",
  "previous":"replace-with-previous-secret"
}'
HUMANQUEUE_HUMAN_JWT_ISSUER='https://identity.example/humans'
HUMANQUEUE_HUMAN_JWT_AUDIENCE='humanqueue-human'
```

Machine configuration uses the same shape with the `HUMANQUEUE_MACHINE_*`
prefix.

The provider validates:

```text
alg == HS256
kid -> configured key
HMAC-SHA256 signature
iss
aud
exp
optional nbf
actor claim (sub by default)
optional request-body actor consistency
```

Multiple keys may be configured simultaneously so a new `kid` can be rolled
out before the previous key is removed.

Optional settings:

```bash
HUMANQUEUE_HUMAN_JWT_ACTOR_CLAIM=sub
HUMANQUEUE_HUMAN_JWT_LEEWAY_SECONDS=30
```

Signed identity provenance is reduced to safe audit fields:

```json
{
  "principal": {
    "kind": "human",
    "provider": "jwt-hs256",
    "issuer": "https://identity.example/humans",
    "audience": "humanqueue-human",
    "kid": "current"
  }
}
```

The compact JWT, HMAC keys, and arbitrary claims are not copied into durable
audit events.

For deployments requiring asymmetric federation, OIDC discovery, or remote
JWKS rotation, use the pluggable `AuthProvider` boundary with an external
identity implementation instead of treating this HS256 provider as OIDC.


### JWT age, token-id, and revocation controls

The HS256 provider can additionally bound replay exposure:

```bash
HUMANQUEUE_HUMAN_JWT_MAX_TOKEN_AGE_SECONDS=300
HUMANQUEUE_HUMAN_JWT_REQUIRE_JTI=true
HUMANQUEUE_HUMAN_JWT_REVOKED_JTIS='[
  "incident-token-123",
  "compromised-token-456"
]'
```

When a maximum token age is configured, `iat` becomes required and the token
is rejected if it is too old or issued in the future beyond configured leeway.

When `JWT_REQUIRE_JTI=true`, signed tokens must carry a non-empty `jti`.
Configured revoked token IDs fail closed even if the JWT signature, issuer,
audience, and expiry are otherwise valid.

HumanQueue does not persist the raw `jti` in its execution audit. If a token ID
is present, audit may retain only a short SHA-256-derived `token_id_hash` so an
incident can correlate events without copying the original token identifier.

The environment revocation list is loaded at process startup. It is deliberately
not described as an online revocation service or dynamic CRL. Deployments that
need immediate distributed revocation should implement that policy behind the
`AuthProvider` boundary or restart/reload the runtime after configuration
changes.


## Tamper-evident audit chain

HumanQueue audit events now form one global SHA-256 hash chain across the SQLite
audit log.

Each event persists:

```text
prev_hash
event_hash
```

The hash covers the canonical event identity and payload:

```text
id
wait_id
event_type
actor
created_at
data_json
prev_hash
```

Verify the chain through:

```http
GET /api/audit/verify
```

A healthy response includes:

```json
{
  "ok": true,
  "checked": 42,
  "head_hash": "..."
}
```

If an event payload, hash link, or middle row is modified/deleted, verification
returns `ok: false` and identifies the first broken event.

Legacy databases whose audit table has never had hashes are backfilled once
during schema migration. Once any chain hashes exist, startup **never rewrites
or auto-heals them**. This prevents a restart from silently laundering a
tampered audit history.

Concurrent writers are serialized by SQLite write locking: HumanQueue inserts
the row first to obtain its monotonic event ID, then links it to the immediately
preceding event hash within the same transaction.

This is **tamper-evident**, not tamper-proof. An attacker with unrestricted
database access could rewrite the full chain. Stronger deployments should
periodically anchor the reported head hash outside the database (for example in
an append-only log, transparency service, signed checkpoint, or external audit
store).


## Signed audit checkpoints outside SQLite

The local audit hash chain is now optionally anchored to a separate signed
JSONL checkpoint file. The checkpoint signing key is process configuration and
is never persisted in SQLite or the checkpoint file.

Legacy single-key configuration:

```bash
export HUMANQUEUE_AUDIT_CHECKPOINT_FILE=/var/lib/humanqueue/audit-checkpoints.jsonl
export HUMANQUEUE_AUDIT_CHECKPOINT_KEY='replace-with-checkpoint-secret'
export HUMANQUEUE_AUDIT_CHECKPOINT_KEY_ID='v1'
```

Create and verify checkpoints without running the HTTP server:

```bash
python human-queue/audit_checkpoint.py --db /var/lib/humanqueue/queue.db create
python human-queue/audit_checkpoint.py --db /var/lib/humanqueue/queue.db verify
```

The CLI path allows the signing key to be held by a separate process / cron
environment rather than the serving process.

HTTP mode is also available when the signer is configured in the server:

```http
POST /api/audit/checkpoint
GET  /api/audit/checkpoint/verify
```

Each checkpoint signs:

```text
version
sequence
created_at
event_count
head_hash
previous_signature
key_id
```

and each checkpoint includes the previous checkpoint signature. This detects
checkpoint edits, insertion/reordering, and middle-row deletion.

### Key rotation

Use a keyring so old checkpoints remain verifiable while new checkpoints move
to a new signing key:

```bash
export HUMANQUEUE_AUDIT_CHECKPOINT_KEYS='{
  "v1":"old-secret",
  "v2":"current-secret"
}'
export HUMANQUEUE_AUDIT_CHECKPOINT_SIGNING_KEY_ID='v2'
```

Do not remove `v1` from the verifier until every checkpoint signed with that
key is outside the verification horizon. An unknown historical `key_id`
fails closed.

### Tail rollback floor

A signed chain cannot, by itself, prove that an attacker did not truncate the
*tail* of the checkpoint file. Deployments that maintain a sequence expectation
outside the checkpoint file can enforce:

```bash
export HUMANQUEUE_AUDIT_CHECKPOINT_MIN_SEQUENCE=42
```

If the local checkpoint file contains fewer than 42 signed checkpoints,
verification reports `checkpoint_rollback_detected`.

The sequence floor must itself come from a trust boundary outside the protected
file (for example deployment configuration, an external witness, or a control
plane).

### Writer serialization

Checkpoint append uses both an in-process lock and a filesystem lockfile:

```text
<checkpoint-file>.lock
```

This prevents two server/CLI processes from concurrently deriving the same
`previous_signature` and creating a fork. Stale lockfiles may be recovered
after the configured stale interval.

Optional settings:

```bash
HUMANQUEUE_AUDIT_CHECKPOINT_LOCK_TIMEOUT_SECONDS=5
HUMANQUEUE_AUDIT_CHECKPOINT_STALE_LOCK_SECONDS=60
```

### Health integration

`GET /api/health` now verifies the local audit chain and, when configured,
the signed checkpoint chain.

Healthy integrity returns HTTP 200. A broken audit chain or invalid checkpoint
returns HTTP 503 so ordinary monitoring can detect provenance damage.

A configured signer with no checkpoints yet is explicitly reported as
`anchored: false`; that is visible but not treated as corruption.

### Threat-model boundary

This HMAC checkpoint protects against an attacker who can rewrite the SQLite
database but does not possess the checkpoint signing secret / trusted external
checkpoint state.

It is not a public, asymmetric attestation. An attacker who controls the
database, checkpoint file, and signing secret can forge new history. Stronger
deployments should move checkpoint publication to an external append-only
witness or use an asymmetric signing provider whose verification key can be
distributed independently.


### Pluggable checkpoint signature providers

Checkpoint signing is now abstracted behind:

```python
class CheckpointSignatureProvider(Protocol):
    @property
    def signing_key_id(self) -> str: ...

    def sign(self, payload: str) -> str: ...

    def verify(
        self,
        payload: str,
        *,
        key_id: str,
        signature: str,
    ) -> bool: ...
```

The built-in implementation remains HMAC-SHA256 and preserves all existing
single-key and keyring environment configuration.

Custom deployments can provide another signer/verifier without changing the
checkpoint chain, audit verification, health checks, or HTTP APIs. This is the
intended boundary for KMS/HSM-backed signatures or a carefully implemented
asymmetric signing service.

HumanQueue deliberately does not implement home-grown Ed25519/RSA primitives in
the stdlib core. Asymmetric/public verification should be supplied through this
provider boundary using a mature cryptographic or managed-key implementation.


## Independent audit witness

HumanQueue can now publish a signed checkpoint to a separate witness service and
receive a witness-signed receipt.

The trust sequence is:

```text
HumanQueue audit chain
  -> signed checkpoint
  -> external witness /witness
  -> witness stores exact checkpoint fingerprint
  -> witness signs receipt
  -> HumanQueue /verify checks receipt against witness state
```

The receipt binds:

```text
witness
receipt_id
received_at
checkpoint_sequence
checkpoint_signature
checkpoint_head_hash
checkpoint_fingerprint
witness key_id
witness signature
```

The full checkpoint fingerprint prevents a receipt from being reused for a
different checkpoint object that merely shares one visible field.

### Run the reference witness service

Start a separate process with a separate signing secret:

```bash
export HUMANQUEUE_WITNESS_KEY='replace-with-witness-secret'
export HUMANQUEUE_WITNESS_KEY_ID='w1'
export HUMANQUEUE_WITNESS_NAME='control-plane-witness'
export HUMANQUEUE_WITNESS_LOG=/var/lib/humanqueue-witness/witness.jsonl

python human-queue/witness_server.py
```

By default it listens on `127.0.0.1:8876`.

It exposes:

```http
POST /witness
POST /verify
GET  /health
```

The reference witness stores the exact signed checkpoint it observed. Its
`/verify` endpoint validates both the witness receipt signature and the fact
that the exact receipt exists in the witness's own durable log.

Replaying the same checkpoint is idempotent and returns the original receipt.

### Protect witness publication

The witness can require a separate publish token:

```bash
export HUMANQUEUE_WITNESS_PUBLISH_TOKEN='publish-only-token'
```

HumanQueue can send that token with:

```bash
export HUMANQUEUE_AUDIT_WITNESS_PUBLISH_TOKEN='publish-only-token'
```

The publish token authorizes submission only. It is not the witness signing key
and does not let HumanQueue forge witness receipts.

The `/verify` endpoint remains independently usable without the publish token.

### Prefer online verification for an independent trust domain

Configure HumanQueue with separate publish and verify endpoints:

```bash
export HUMANQUEUE_AUDIT_WITNESS_URL='https://witness.example/witness'
export HUMANQUEUE_AUDIT_WITNESS_VERIFY_URL='https://witness.example/verify'
```

In this mode HumanQueue does **not** possess the witness signing secret.
Verification is delegated back to the independent witness.

A shared-key verifier is still supported for development or closed deployments:

```bash
export HUMANQUEUE_AUDIT_WITNESS_KEYS='{"w1":"shared-secret"}'
```

but shared HMAC verification is not a truly independent trust domain because a
verifier that holds the HMAC key can also mint signatures.

For real trust separation, prefer online verification or a future asymmetric
witness verifier whose public key can be distributed without signing authority.

### Persist witness receipts

HumanQueue can persist verified receipts separately:

```bash
export HUMANQUEUE_AUDIT_WITNESS_RECEIPTS_FILE=/var/lib/humanqueue/witness-receipts.jsonl
```

Receipt journal writes use an inter-process lockfile and recover stale locks.
Health checks re-verify persisted receipts rather than treating file presence as
proof.

The health state distinguishes:

```text
checkpoint signed
witness configured
receipt journal configured
latest checkpoint witnessed
witness verification unavailable
invalid witness receipt
```

A witness verification outage is reported separately from cryptographic receipt
failure.

## Multi-witness quorum

A deployment can require multiple independent witnesses rather than relying on
one witness as a single trust point.

Example:

```bash
export HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON='{
  "threshold": 2,
  "required_witnesses": ["security-witness"],
  "witnesses": {
    "security-witness": {
      "url": "https://security.example/witness",
      "verify_url": "https://security.example/verify",
      "publish_token": "..."
    },
    "operations-witness": {
      "url": "https://ops.example/witness",
      "verify_url": "https://ops.example/verify"
    },
    "external-witness": {
      "url": "https://external.example/witness",
      "verify_url": "https://external.example/verify"
    }
  }
}'
```

This example requires:

```text
at least 2 distinct witnesses
AND security-witness must be one of them
```

Publish the latest signed checkpoint to the configured quorum:

```http
POST /api/audit/checkpoint/witness-quorum
```

The response reports:

```text
satisfied
threshold
confirmed_witnesses
required_witnesses
missing_required_witnesses
receipts
per-witness failures
```

Duplicate receipts from one witness never count twice. A receipt whose
self-declared witness identity does not match the configured target is rejected.

When quorum is explicitly configured, HumanQueue requires both checkpoint
signing and a durable witness receipt journal. Once a signed checkpoint exists,
`/api/health` returns HTTP 503 until the configured quorum is satisfied.

Before the first checkpoint exists, quorum is visible as configured but
unsatisfied without marking an otherwise empty runtime unhealthy.

### Trust progression

The evidence model is now intentionally layered:

```text
local audit hash chain
  -> locally signed checkpoint
  -> independently witnessed checkpoint
  -> durable signed receipt
  -> N-of-M witness quorum
```

Each layer answers a different question. HumanQueue should not describe a local
HMAC checkpoint as externally witnessed, nor a single witness receipt as a
quorum.


## Evidence snapshot and offline evidence bundle

HumanQueue now exposes one stable read-only evidence view instead of requiring
operators to manually correlate audit, checkpoint, witness, and quorum APIs.

Read the current snapshot:

```http
GET /api/evidence
```

The snapshot uses schema:

```text
humanqueue.evidence.v1
```

and contains:

```text
audit_chain
checkpoint.latest + checkpoint.verification
witness status + persisted receipts
quorum policy/result
policy_ok
evidence_id
generated_at
```

`evidence_id` is a canonical SHA-256 digest of the evidence content and does
not include `generated_at`. Re-reading unchanged evidence therefore preserves
the same ID even when the observation time changes.

`/api/health` is derived from the same evidence builder, so health and evidence
cannot silently drift into different policy semantics.

### Export a complete evidence bundle

The snapshot is useful for status, but it is not by itself sufficient for
independent replay. A complete bundle additionally carries the exact audit hash
inputs:

```text
raw audit records including original data_json
all signed checkpoints
persisted witness receipts
current evidence snapshot
```

Export over HTTP:

```http
GET /api/evidence/bundle
```

When human authentication is configured, this endpoint requires a valid human
principal. The bundle can contain execution/audit payloads, so it should be
handled as audit data even though signing keys, bearer tokens, JWTs, and witness
secrets are not included.

Export directly from a runtime database:

```bash
python human-queue/evidence_bundle.py export \
  --db /var/lib/humanqueue/queue.db \
  --output /tmp/humanqueue-evidence.json
```

Then move the JSON file to another machine and verify it without opening the
HumanQueue SQLite database:

```bash
python human-queue/evidence_bundle.py verify \
  /tmp/humanqueue-evidence.json
```

Default offline verification checks:

```text
bundle_id canonical hash
audit event hash chain using the original persisted data_json
checkpoint ordering and previous-signature linkage
checkpoint -> audit-head boundary binding
witness receipt -> checkpoint signature/head/fingerprint binding
snapshot evidence_id
snapshot audit summary -> exported audit records
```

This mode proves **structural integrity and binding consistency**. It deliberately
reports checkpoint and witness signature authenticity as `not_checked` unless
verification material is supplied.

### Strict offline authenticity verification

For local HMAC deployments, load verification keyrings from environment and run:

```bash
python human-queue/evidence_bundle.py verify --strict \
  /tmp/humanqueue-evidence.json
```

Strict mode reuses the existing environment shapes:

```text
HUMANQUEUE_AUDIT_CHECKPOINT_KEYS
or HUMANQUEUE_AUDIT_CHECKPOINT_KEY + HUMANQUEUE_AUDIT_CHECKPOINT_KEY_ID

HUMANQUEUE_AUDIT_WITNESS_QUORUM_JSON with per-witness local keys
or HUMANQUEUE_AUDIT_WITNESS_KEYS
```

Keys are intentionally read from environment rather than command-line options so
they are not encouraged into shell history.

Once strict verification is requested, it fails closed:

```text
checkpoint exists but no checkpoint verifier -> failure
unknown checkpoint key id -> failure
invalid checkpoint signature -> failure
receipt exists but witness verifier is missing -> failure
invalid witness receipt signature -> failure
```

A successful strict result reports:

```json
{
  "authenticity": {
    "checkpoint_signatures": "verified",
    "witness_receipt_signatures": "verified"
  }
}
```

### Verification boundary

A bundle hash is not a signature. An attacker who can rewrite a bundle can also
recompute its outer `bundle_id`. The security progression is therefore:

```text
bundle hash / structural replay
  -> signed checkpoint verification
  -> witness receipt verification
  -> independent witness state / quorum
```

The stdlib CLI can perform local HMAC authenticity checks. Online independent
witness verification and custom asymmetric/KMS/HSM verification remain provider
concerns; the verifier does not claim those checks occurred when it only has a
self-contained JSON file.

This distinction is intentional:

> **self-consistent evidence is not the same claim as independently authenticated evidence.**
