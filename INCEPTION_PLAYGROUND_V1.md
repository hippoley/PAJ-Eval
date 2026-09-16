# Inception Playground v1/v2

## Product promise

A participant should experience a small useful cognitive shift before being asked to understand the research. The interface must demonstrate the phenomenon rather than explain it.

## Invariant interaction contract

1. No essay-first elicitation.
2. Every probe is an ordinary action inside a concrete micro-world.
3. The target cognitive structure is never named before baseline behavior is observed.
4. Intervention is minimal: one experiential reframing, not a lesson.
5. The intervention is then removed.
6. Transfer worlds change surface and domain.
7. Later behavior must be possible without repeating target vocabulary.
8. The system records behavior trajectories, not only terminal answers.
9. A participant may ignore, reject, or outgrow the intervention.
10. Strong transfer is not automatically good: over-application must be measured.
11. Participant-facing value and research value must arise from the same interaction.
12. Scores shown in the prototype are exploratory signals, never claims about a participant.

## v2 correction: natural-world affordances

The participant-facing interface must expose **real objects, not research variables**.

A button is valid only when the same action would make sense if this were a real shop, inbox, trip planner, IDE, dashboard, or workspace. Examples: open a device, open a contract, inspect a team page, open a map, view an airport page, book a flight. Invalid primary affordances include labels such as `compatibility`, `hidden constraint`, `future option`, or `look closer` when those phrases exist only because the researcher wants a particular construct measured.

The design rule is:

`front end: concrete objects and ordinary actions -> event stream -> inference layer: abstract latent hypotheses`

The user must know what an action does while remaining unable to infer which action the researcher wants. There is no required correct path. Multiple different trajectories may support the same latent explanation, and the same action may support competing explanations.

Research inference must remain downstream of behavior. The prototype therefore separates:

- factual event layer: what object was opened, when, in what world, and what decision followed;
- semantic tags: candidate meanings such as downstream constraint, diligence, risk, convenience, or future-option search;
- latent hypotheses: competing explanations updated from the trajectory.

No participant-facing score should be computed directly from one privileged click.

## Current target

`downstream_option_structure`

Working structure: visible choices can conceal downstream constraints and option-value consequences.

The participant is not taught this as a proposition. The first shopping world creates an experience in which a visible price advantage can reverse after compatibility constraints appear. A minimal intervention then names only the shape of the experience. Career and travel worlds remove the wording and test whether related information is sought spontaneously through ordinary interfaces.

## Vertical slice

`shopping baseline -> consequence -> minimal intervention -> career transfer -> travel transfer -> local research view`

### Shopping baseline

The participant can use a normal product surface: products, their own devices, reviews, delivery/returns, and search. The research layer observes navigation and commitment. Compatibility is not a dedicated research button.

### Consequence

If the cheaper visible choice is selected, checkout reveals the bridge requirement and changed total cost. The participant can continue, change the product, or inspect the affected devices. There is no correctness feedback.

### Minimal intervention

One sentence opens the downstream-option shape. It must not become a tutorial.

### Career transfer

The surface changes to an offer inbox with offer pages, company pages, contracts, team descriptions, calendar, and map. The participant can decide immediately or navigate naturally. No `look closer` control is supplied.

### Travel transfer

The surface changes again to a trip planner: flights, itinerary, airport, hotel, and calendar. No target vocabulary is repeated.

## Event ontology

Core events include:

- `session_start`
- `open_object`
- `open_detail`
- `search_query`
- `commit`
- `post_consequence_action`
- `intervention_exposed`
- `session_complete`

Every event records elapsed time. Object events may carry hidden semantic tags used only by the inference layer.

## Measurement status

The current browser profile is UX instrumentation only. It is not a validated PAJ score. It exists to make the complete causal story observable during dogfood.

Before human-effect claims, add:

- counterfactual twin worlds;
- no-intervention control;
- delayed transfer;
- blinded behavioral coding;
- surface invariance tests;
- overreach worlds where the inception structure should *not* be applied;
- persistence measurement after assistance is absent;
- preregistered scoring and falsification gates.

## Architecture direction

The static prototype intentionally keeps world transitions deterministic. The next implementation should separate:

- `World Renderer`: participant-facing micro-worlds;
- `Session Runtime`: state and event stream;
- `Probe Engine`: latent hypotheses and next-probe selection;
- `Inception Engine`: intervention dosage, fading, transfer sequencing;
- `PAJ Evaluator`: no-AI transfer and persistence;
- `Research Console`: trajectory replay and aggregate validity analysis.

LLMs may later generate surface language or candidate worlds, but must not silently alter experimental state transitions in confirmatory runs.
