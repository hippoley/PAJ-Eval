# PAJ-Eval

PAJ-Eval is a playable research instrument for observing how people notice, frame, investigate, revise, stop, and act across small decision worlds.

## v4.1 participant surface

The canonical participant surface is `docs/index.html`. It contains PF01–PF08, the complete ten-locale scenario catalog, consent/local-only controls, durable IndexedDB-first submission, stable `client_submission_id` retry, and raw-trajectory export.

The old `docs/live.html` URL is now only a compatibility alias to the canonical player. There is intentionally no second embedded probe catalog or second persistence implementation.

GitHub Pages participant route:

`https://hippoley.github.io/PAJ-Eval/`

Researcher route:

`https://hippoley.github.io/PAJ-Eval/research.html`

The researcher browser authenticates through Supabase Auth and calls the JWT-protected `research-sessions` Edge Function; it does not expose a service-role key in the browser.

## Durable research chain

```text
participant
  -> Probe Player
  -> session
  -> probe_run
  -> append-only raw events
  -> versioned derived_features
  -> versioned evaluations
```

Raw trajectory is evidence, not a personality score. Feature extraction and evaluation remain versioned, replaceable layers linked back to source events.

## v4.1 completion contract

The non-regression contract lives in [`V4_DESIGN_CONTRACT.md`](V4_DESIGN_CONTRACT.md). In particular, v4.1 requires:

- PF01–PF08 in one canonical player.
- Ten complete scenario-level locale catalogs with no silent English fallback.
- Truthful local-only / saving / saved / save-failed states.
- IndexedDB queue commit before the first network attempt.
- Stable idempotency keys and ordered retry.
- Synthetic CI tests for offline retention, duplicate coalescing, and retry ordering.
- Researcher-only replay of persisted trajectories.

## Tests

```bash
pytest -q
node --test tests/transport.test.js
```

The Node tests exercise the durable transport independently of the UI: a failed submission remains queued, retry reuses the same id, concurrent duplicates coalesce to one network call, and an outage cannot let later submissions overtake an earlier failed item.

## Research status

PAJ-Eval is an instrument-development repository. A playable trajectory is not, by itself, a validated psychological construct or validated score. Confirmatory claims require counterfactual worlds, blinded coding/oracle checks, transfer tests, multilingual semantic-equivalence validation, and treatment comparison.
