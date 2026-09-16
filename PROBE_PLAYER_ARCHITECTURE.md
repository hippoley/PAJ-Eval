# Probe Player architecture

Probe Player is the experience layer. Its job is to make a participant want to act inside a small world while producing a clean event stream. It should not expose latent causes, research labels, or a preferred click path.

The architecture has four separable layers:

```text
Probe Player (experience)
  -> Session Event Stream (facts)
  -> PAJ Measurement (features, constructs, scores)
  -> Experiment Layer (counterfactuals, transfer, treatment effects)
```

## Experience layer

Render different micro-worlds with domain-native affordances: inbox, dashboard, store, itinerary, research notebook, IDE, calendar, or project workspace. A visible control must mean what it would mean outside the experiment. The same renderer should be able to host causal twins without changing the interaction grammar.

## Event stream

Minimum event fields: session_id, probe_family, world_variant, locale, phase, event_type, object_id, elapsed_ms, world_state_before, world_state_after, evidence_exposed, intervention_exposure, and commitment where applicable.

The event stream records facts. Hidden construct tags belong in a separate analysis registry, never in participant-visible markup and preferably not in exported raw participant traces.

## Measurement layer

Transforms events into preregistered features and scores. It owns SDO, ERU, regret, calibration, cost accounting, blinded coding joins, and oracle comparisons. This layer must preserve alternative explanations and uncertainty rather than turn every click into a trait score.

## Experiment layer

Owns randomization, treatment packet hashes, causal twins, surface variants, near/far transfer, no-AI phases, delayed measurement, arm-level assisted-performance equivalence gates, and treatment-effect estimation.

The long-term platform goal is that a new probe family can supply a world specification, evidence model, action model, renderer mapping, and measurement contract without rewriting the player.