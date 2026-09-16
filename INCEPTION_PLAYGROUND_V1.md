# Inception Playground v1

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

## v1 target

`future_option_hidden_constraint`

Working structure: visible choices can conceal downstream constraints and option-value consequences.

The participant is not taught this as a proposition. The first shopping world creates an experience in which a visible price advantage can reverse after compatibility constraints appear. A minimal intervention then names only the shape of the experience. Career and travel worlds remove the wording and test whether related information is sought spontaneously.

## Vertical slice

`shopping baseline -> consequence -> minimal intervention -> career transfer -> travel transfer -> local trace`

### Shopping baseline

Behavioral signals include first inspection, inspection order, whether compatibility is sought before commitment, and initial commitment.

### Consequence

If the cheaper visible choice is selected, a downstream bridge cost is revealed. The participant can keep, reconsider, or inspect further. There is no correctness feedback.

### Minimal intervention

One sentence opens the downstream-option frame. It must not become a tutorial.

### Career transfer

The surface changes from products to employment. The participant can commit immediately or look closer. Role mobility is one relevant downstream-option signal, but the UI must not claim it is the only rational consideration.

### Travel transfer

No explicit `look closer` call to action. Ordinary itinerary affordances remain available. Arrival and ground-transport inspection can reveal downstream constraints.

## Event ontology

Core events:

- `session_start`
- `inspect`
- `commit`
- `hidden_constraint_avoided`
- `update_after_constraint`
- `intervention_exposed`
- `career_action`
- `session_complete`

Every event records elapsed time. Inspect events record world, target, whether prompted, and whether after intervention.

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

The static v1 intentionally keeps world transitions deterministic. The next implementation should separate:

- `World Renderer`: participant-facing micro-worlds;
- `Session Runtime`: state and event stream;
- `Probe Engine`: latent hypotheses and next-probe selection;
- `Inception Engine`: intervention dosage, fading, transfer sequencing;
- `PAJ Evaluator`: no-AI transfer and persistence;
- `Research Console`: trajectory replay and aggregate validity analysis.

LLMs may later generate surface language or candidate worlds, but must not silently alter experimental state transitions in confirmatory runs.
