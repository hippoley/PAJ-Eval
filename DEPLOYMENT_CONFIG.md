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
- anonymous ingestion function: `ingest-probe` — ACTIVE v4
- researcher read function: `research-sessions` — ACTIVE v3

No service-role/database/admin secret belongs in GitHub Pages, the repository, or a participant browser.

## Server-side idempotency, consent, and atomicity

The historical migration `supabase/migrations/20260917_atomic_probe_ingestion_v2.sql` defines the first atomic RPC. The current branch adds `supabase/migrations/20260918_consent_aware_ingestion_v4.sql`, which defines `ingest_probe_atomic_v4(...)` and stores the explicit `consent_version` supplied by the participant flow while preserving rich event payload fields.

The server boundary must independently guarantee what the browser cannot:

- `sessions.client_submission_id` is unique when present;
- a duplicate submission returns the already-created `session_id` rather than creating a second session;
- session, probe run, and event writes are one atomic database operation;
- only the service-role path may execute the ingestion RPC directly.

### Deployed verification — 2026-09-17

A synthetic PF01 submission was executed directly against the deployed v2 RPC using one UUID twice. The first invocation returned `duplicate=false`; the second returned `duplicate=true`; both returned the same session id. A follow-up database read showed exactly one session, one probe run, and two events for that submission. The synthetic session was then deleted after verification.

### Consent-aware rich-event verification — 2026-09-18

The canonical project now has both current migrations applied:

- `20260918020957 consent_aware_ingestion_v4`;
- `20260918021248 research_replay_indexes`.

The deployed functions are:

- `ingest-probe` ACTIVE v4, with the existing anonymous-ingestion boundary preserved (`verify_jwt=false`) and origin/payload validation performed in the function body;
- `research-sessions` ACTIVE v3 with `verify_jwt=true` and the researcher-role check still fail-closed.

A synthetic PF08 record was executed directly against `ingest_probe_atomic_v4(...)` with `golden-consent-v1`, then submitted again with the same client UUID. The duplicate call returned the existing session. A database read verified:

- `consent_version = golden-consent-v1`;
- `instrument_version = golden-pf08-v1`;
- `client_schema_version = v4-rich-events`;
- `probe_family = PF08`;
- the rich `payload_json` retained `market`, `study_version`, `envelope_version`, `raw_event_type`, and the nested original raw event including relation/omission-style fields.

The synthetic verification session was deleted afterward and a follow-up count returned zero remaining rows for its client submission id.

This verifies the deployed database/RPC path and deployed function source versions. The formal browser HTTP path and authenticated researcher-browser replay are still separate release gates.


## Formal Golden study flow

The Golden-depth journeys remain ordinary local previews unless the participant enters through `docs/study.html?family=PF01..PF08&locale=<locale>` and explicitly checks the consent box.

The consented path is:

```text
study.html
  → explicit consent
  → sessionStorage consent context + stable client_submission_id
  → direct journey with ?study=1
  → golden-study-bridge.js
  → lazy-load golden-event-normalizer.js + transport.js
  → isolated IndexedDB queue paj-golden-study-queue-v1
  → ingest-probe
  → ingest_probe_atomic_v4(...)
```

Important boundaries:

- preview journeys do not load the durable transport or open IndexedDB;
- the study bridge refuses submission without a fresh consent context, matching PF family, locale, and stable UUID;
- the formal queue is isolated from the canonical player queue so a stale unrelated submission cannot block a study retry;
- raw family-specific events are retained inside the normalized event envelope rather than flattened away;
- participant pages still do not expose PF labels or latent construct names.

The v4 consent-aware migration and updated Edge Functions are now deployed. Formal Golden collection should still remain gated until one consented browser submission is exercised through `study.html` → journey → `ingest-probe`, and the resulting session is replayed through an authenticated researcher account. Database/RPC deployment alone is not the same as a completed browser-level release smoke test.

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

The browser now supports sessions containing multiple probe runs. Events and derived features are grouped by `probe_run_id`, each run is replayed independently, orphan events are surfaced explicitly, and a session can be opened directly with `research.html?session_id=<uuid>`. Each event can also be expanded to inspect its stored `payload_json`, which is required for Golden family-specific fields such as experiment budget, delayed-check timing, objective-artifact state, and PF08 relation/omission traces.

## Researcher-account operational gate

As checked again on 2026-09-18, the canonical Supabase project currently has **zero** Auth accounts whose `app_metadata.role = researcher`.

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
