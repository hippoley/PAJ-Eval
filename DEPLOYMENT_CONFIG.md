# PAJ-Eval Deployment Configuration

PAJ-Eval deliberately separates public source code from deployment ownership. A fork must not silently inherit the canonical research backend.

## Participant surface

The canonical participant surface is `docs/index.html`. It reads the shared ten-locale catalog from `docs/locales.js` and uses the shared durable browser transport in `docs/transport.js`.

The transport contract is:

1. create a stable `client_submission_id`;
2. commit the full submission to IndexedDB before the first network attempt;
3. POST to the deployment-owned ingestion endpoint;
4. delete the queued item only after an explicit durable acknowledgement containing a `session_id`;
5. retry queued submissions in original order and reuse the same id;
6. coalesce concurrent duplicate sends for the same id in the browser.

The public player exposes truthful persistence states rather than claiming persistence simply because a request was attempted.

## Canonical backend

Current canonical deployment:

- Supabase project: `pwdcgfvarudhqezlzwmx`
- anonymous ingestion function: `ingest-probe`
- researcher read function: `research-sessions`

No service-role/database/admin secret belongs in GitHub Pages, the repository, or a participant browser.

## Server-side idempotency and atomicity

The database migration `supabase/migrations/20260917_atomic_probe_ingestion_v2.sql` defines `ingest_probe_atomic(...)`.

The server boundary must independently guarantee what the browser cannot:

- `sessions.client_submission_id` is unique when present;
- a duplicate submission returns the already-created `session_id` rather than creating a second session;
- session, probe run, and event writes are one atomic database operation;
- only the service-role path may execute the ingestion RPC directly.

### Deployed verification — 2026-09-17

A synthetic PF01 submission was executed directly against the deployed RPC using one UUID twice. The first invocation returned `duplicate=false`; the second returned `duplicate=true`; both returned the same session id. A follow-up database read showed exactly one session, one probe run, and two events for that submission. The synthetic session was then deleted after verification.

This verifies deployed server-side idempotency and atomic insertion behavior rather than only repository source text.

## Research Session Browser

`docs/research.html` is researcher-only. It signs in with Supabase Auth and calls the JWT-protected `research-sessions` Edge Function.

Required authorization boundary:

```text
valid Supabase user JWT
        +
user.app_metadata.role = researcher
        ↓
research-sessions
        ↓
session / probe_runs / ordered events / derived_features / evaluations
```

The researcher API must fail closed. If probe runs, events, derived features, or evaluations cannot be read successfully, the API returns `research_read_failed` instead of presenting a partial trajectory as complete.

The browser now supports sessions containing multiple probe runs. Events and derived features are grouped by `probe_run_id`, each run is replayed independently, orphan events are surfaced explicitly, and a session can be opened directly with `research.html?session_id=<uuid>`.

## Researcher-account operational gate

As checked on 2026-09-17, the canonical Supabase project currently has **zero** Auth accounts whose `app_metadata.role = researcher`.

Do not weaken `verify_jwt`, expose database SELECT to anonymous users, or embed a service-role key merely to get through the final smoke test.

Operational release still requires a deliberately provisioned researcher account, followed by:

1. sign in through `docs/research.html`;
2. persist one synthetic PF session through the participant ingestion path;
3. verify the session appears in the session list;
4. open the session (or deep-link directly to its UUID);
5. verify the browser replays every probe run and ordered event;
6. verify derived features/evaluations render as their current versioned layers;
7. remove the synthetic session if it is only release-test data.

Until that authenticated browser replay is performed, the branch can be code-complete but should not be described as operationally released.
