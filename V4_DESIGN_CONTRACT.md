# PAJ-Eval v4 design contract

This document is a non-regression contract. A dogfood page, deployment shortcut, or UI rewrite MUST NOT silently narrow these requirements.

## Instrument architecture

The durable research chain is:

`participant -> Probe Player -> session -> probe_run -> append-only events -> versioned derived_features -> versioned evaluations`

Raw trajectory is the sensor, not the conclusion. Raw events are immutable research evidence. Feature extraction and scoring are replaceable, versioned derivations and must retain evidence links back to source events.

The complete instrument must support session replay, blinded coding, counterfactual validation, language-invariance analysis, and treatment comparison without rewriting raw participant history.

## Probe coverage

PF01-PF08 remain one coherent Probe Player. `live.html` is a dogfood/transport diagnostic and MUST NOT replace the complete player.

Every persisted event carries enough metadata to identify at least instrument/copy version, locale, probe family, world/variant, phase/event type, elapsed time, and inspected object/terminal action where applicable.

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

After locale selection, every participant-facing string must come from that locale's complete scenario-level catalog: shell, probe title, situation, inspectable object labels/descriptions, reveals, decisions, navigation, persistence status, consent/error copy, and any participant-visible result copy.

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

The full player keeps a browser-side queue (IndexedDB preferred) before upload. Network failure must not erase the raw trajectory. Retry is idempotent and preserves event ordering.

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

A release is not called v4-complete merely because a live POST succeeds. Completion requires the full PF01-PF08 player, complete ten-locale catalog with no English fallback, truthful four-state persistence UI, recoverable queued events, durable server storage, and a researcher-readable session trajectory.