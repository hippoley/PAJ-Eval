# PAJ-Eval

> Same task success. Different humans afterward?

PAJ-Eval is a research instrument for studying whether AI assistance changes a person's later judgment after the assistant is gone: noticing, framing, investigating, revising, stopping, and acting on a new problem that has not already been specified for them.

The repository deliberately separates **raw behavior**, **versioned feature extraction**, and **versioned evaluation**. A trajectory is evidence, not a personality score.

## v4.1 playable instrument

The active completion work is in PR #12 (`v4-complete-rebase`). The canonical participant surface is `docs/index.html` and the researcher surface is `docs/research.html`.

The current branch includes:

- one PF01–PF08 canonical Probe Player;
- ten complete participant-language scenario catalogs;
- IndexedDB commit-before-network persistence;
- stable `client_submission_id` retry semantics and concurrent duplicate coalescing;
- server-side atomic ingestion through `ingest_probe_atomic(...)`;
- a unique `sessions.client_submission_id` idempotency boundary;
- truthful local-only / saving / saved / queued-failure states;
- JWT-protected researcher reads requiring `app_metadata.role = researcher`;
- ordered raw-event replay with versioned derived-feature and evaluation layers;
- CI contract tests plus synthetic Node transport tests.

The deployed backend idempotency rule has been verified: repeating the same client submission id resolves to the same session and does not create a second trajectory. The researcher Edge Function has also been hardened so failed component reads return an error instead of silently showing an incomplete replay.

The remaining **operational** release gate is authenticated browser replay. A Supabase Auth account with `app_metadata.role = researcher` must be provisioned, then one synthetic persisted session must be opened through `docs/research.html` and checked end-to-end. The role boundary should not be weakened to bypass this step. See [`DEPLOYMENT_CONFIG.md`](DEPLOYMENT_CONFIG.md).

## Development checks

```bash
pytest -q
node --test tests/transport.test.js
```

The transport tests cover queue-before-network, offline retention, same-id retry, duplicate coalescing, and ordered retry that stops at the first failure.

## Repository map

- `docs/index.html` — canonical participant player
- `docs/locales.js` — ten-language scenario catalog
- `docs/transport.js` — durable browser transport
- `docs/research.html` — researcher-only replay browser
- `supabase/functions/ingest-probe/` — anonymous validated ingestion boundary
- `supabase/functions/research-sessions/` — JWT + researcher-role read boundary
- `supabase/migrations/20260917_atomic_probe_ingestion_v2.sql` — atomic/idempotent ingestion RPC
- `V4_DESIGN_CONTRACT.md` — non-regression contract
- `PROBE_FAMILIES.md` — measurement families and growth/falsification requirements

## Research principle

Task success alone is not enough to tell us what kind of judgment remains afterward. PAJ-Eval therefore keeps the observable path inspectable and treats all higher-level constructs as replaceable, testable interpretations tied back to evidence.
