# Deployment configuration

PAJ-Eval separates public source code from deployment ownership. A fork may reuse the instrument code, but it must not inherit the canonical research database or researcher credentials by default.

## Participant ingestion

The canonical deployment currently uses a Supabase Edge Function named `ingest-probe`. The browser sends pseudonymous trajectory payloads only after explicit consent. Each payload has a stable `client_submission_id`; the server writes the session, probe run, and ordered raw events through the atomic `ingest_probe_atomic(...)` database function.

The deployed database enforces a partial unique index on `sessions.client_submission_id`, and the RPC uses `ON CONFLICT (client_submission_id) ... DO NOTHING`. A retry with the same client id therefore resolves to the already-created session instead of creating a second trajectory.

A deployed-backend verification on 2026-09-17 called the same atomic ingestion RPC twice with one synthetic `client_submission_id`. The first call returned `duplicate=false`; the second returned `duplicate=true` with the **same session id**. A follow-up read confirmed exactly one session, one probe run, and two ordered raw events. The synthetic session was then removed.

Do not place service-role, database, or admin secrets in the browser bundle. The public ingestion Edge Function is the only anonymous write surface.

## Researcher reads

`research-sessions` is a JWT-protected Edge Function. It validates the Supabase user and then requires:

```text
app_metadata.role = researcher
```

The browser never receives the service-role key. Session detail reads fail closed: if probe runs, events, derived features, or evaluations cannot be read, the API returns `research_read_failed` instead of silently rendering a partial trajectory. Invalid session identifiers are rejected before querying.

The deployed `research-sessions` function is currently version 2 with JWT verification enabled.

## Release verification

A deployment is not considered complete until all of the following are true:

1. CI passes Python contract tests and Node durable-transport tests.
2. The deployed ingestion RPC has the `client_submission_id` uniqueness rule and atomic session/run/event write.
3. A synthetic PF01–PF08 submission can be persisted and a duplicate submission returns the same session id without adding a second session or event set.
4. At least one Supabase Auth account has `app_metadata.role = researcher`.
5. That researcher can open `docs/research.html`, list sessions, select the synthetic session, and see the ordered raw trajectory plus versioned derived/evaluation layers.
6. The temporary synthetic record is removed after verification if it is not intentionally retained as a fixture.

Items 1–3 are now verified. The remaining operational gate is items 4–5: at the time of verification there were **zero** Auth accounts with `app_metadata.role = researcher`, so an authenticated browser replay cannot yet be truthfully claimed. Do not weaken the role boundary merely to make this smoke test easier.

## Local development

Serve `docs/` from one of the allowed local origins (`http://localhost:8000` or `http://127.0.0.1:8000`) so browser CORS behavior matches production closely. Keep local test trajectories clearly labeled and avoid using real participant identity data.
