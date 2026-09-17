# PAJ-Eval v4 design contract

This document is a non-regression contract. A dogfood page, deployment shortcut, or UI rewrite MUST NOT silently narrow these requirements.

## Instrument architecture

The durable research chain is:

`participant -> Probe Player -> session -> probe_run -> append-only events -> versioned derived_features -> versioned evaluations`

Raw trajectory is the sensor, not the conclusion. Raw events are immutable research evidence. Feature extraction and scoring are replaceable, versioned derivations and must retain evidence links back to source events.

The complete instrument must support session replay, blinded coding, counterfactual validation, language-invariance analysis, and treatment comparison without rewriting raw participant history.

## One canonical player

PF01-PF08 are one coherent Probe Player. There must not be a second embedded probe catalog or a second persistence implementation in a `live` page. `docs/index.html` is the canonical participant surface; legacy/live URLs may only alias or redirect to it.

The canonical player reads scenario content from the shared locale catalog and persistence behavior from the shared durable transport module. CI guards against reintroducing duplicate embedded catalogs.

Every persisted event carries enough metadata to identify at least instrument/copy version, locale, probe family, world/variant, phase/event type, elapsed time, sequence, and inspected object/terminal action where applicable.

## Probe coverage

PF01-PF08 remain available from the canonical player. A dogfood/transport diagnostic MUST NOT replace or narrow the complete instrument.

## Localization

Supported participant locales:

- English
- 简体中文
- 繁體中文
- 日本語
- 한국어
- Español
- Français
- Deutsch
- Português
- Русский

After locale selection, every participant-facing scenario string must come from that locale's complete scenario-level catalog: probe title, situation, inspectable object labels/descriptions, reveals, decisions, and participant-visible result copy.

No non-English locale may silently fall back to English. CI must fail when a locale is null, structurally incomplete, or missing PF01-PF08.

Translation validity means semantic/information/cue/affordance equivalence, not literal word-for-word translation.

## Persistence states

The UI exposes truthful persistence state:

- `local only`: no research backend configured or participant chose local mode
- `saving`: accepted locally and currently attempting persistence
- `saved`: server acknowledged durable persistence
- `save failed`: current server attempt failed; local queue/trace remains recoverable

A static GitHub Pages deployment must never claim server persistence unless an actual backend acknowledges it.

## Offline and retry

The full player commits a browser-side IndexedDB queue entry before the first network attempt. Network failure must not erase the raw trajectory. Retry is idempotent through a stable `client_submission_id`, preserves event/submission ordering, and stops at the first unsent item rather than overtaking it.

Concurrent duplicate submission of the same client id must be coalesced client-side. The ingestion backend must enforce the same idempotency key server-side.

The transport behavior is executable specification: CI runs synthetic tests proving offline retention, same-id retry, duplicate coalescing, and ordered retry.

## Deployment isolation

Public source code is reusable. Deployment credentials and ownership are not shared.

A fork does not inherit the canonical research backend by default. Each deployment supplies its own backend endpoint/configuration. Service-role/database/admin secrets never enter the public repository or browser bundle.

## Privacy

Core research persistence is pseudonymous. Do not request/store name, email, account handle, exact location, device fingerprint, or free-form identity fields merely to operate the instrument. Locale is measurement metadata. Explicit consent precedes research persistence.

## Researcher surface

The target researcher flow is:

`Research Session Browser -> session -> probe runs -> ordered raw events -> replay -> versioned features -> versioned evaluations`

Researcher-only reads are separate from anonymous ingestion. Anonymous participants must not gain SELECT access to research tables.

## Completion criterion

A release is not called v4-complete merely because a POST succeeds. Completion requires the canonical PF01-PF08 player, complete ten-locale catalog with no English fallback, truthful four-state persistence UI, recoverable queued events, durable server storage, synthetic transport proof in CI, and a researcher-readable session trajectory.
