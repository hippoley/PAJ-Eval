# PAJ-World v1 — Instrument before treatment

Status: pre-validation research instrument. No human causal claim.

## Research target

PAJ-World v1 asks a narrower question than the eventual PAJ treatment study:

> When no diagnostic question has been supplied, what problem does a technically experienced participant spontaneously open, what evidence do they acquire, how do they update, and when do they act?

The immediate goal is not to show that AI changes people. It is to establish that the environment can measure a reproducible behavioral object before any AI treatment is introduced.

## Why this exists

Judgment-heavy benchmarks increasingly test iterative analysis under ambiguity, but PAJ targets an upstream boundary: the question is not fully specified for the participant. The instrument therefore must not smuggle the target problem into the prompt or interface.

A participant can retain nominal control over a system while depending on the environment to supply the candidate problem representation. PAJ-World separates spontaneous problem opening from later recognition after candidate investigations become visible.

## Measurement chain

`world state → spontaneous opening → evidence acquisition → update trajectory → stopping → terminal action`

Primary instrument signal at this stage:

- **Spontaneous Diagnostic Opening (SDO):** blinded coding of the locked pre-menu first move for whether it independently opens a decision-relevant alternative problem representation.

Secondary behavioral signals:

- first investigation;
- free-form investigation request;
- whether the participant voluntarily opens the available-check menu;
- investigation sequence and cost;
- evidence-dependent direction changes;
- stopping point;
- terminal action / defer;
- requested-but-unavailable investigation;
- perceived wording or visual leakage.

ERU remains the intended primary confirmatory outcome for a later treatment study. SDO is a mechanism endpoint, not a second confirmatory primary.

## World-family design

A useful world family contains two kinds of controlled variation.

### Causal twins

Keep the surface story and action space approximately fixed while changing a latent causal fact such that a different investigation becomes decision-relevant. Behavior should change for the right causal reason.

Current retrieval pair:

- R: representation drift is leading.
- S: stale serving index is leading.

Current feature-serving pair:

- C: model calibration drift is leading.
- F: stale online feature materialization is leading.

### Surface twins

Keep the latent cause fixed while changing rendering, names, ordering, and non-causal surface details. Behavior should remain materially stable.

A benchmark that changes answers under surface edits or fails to change under causal edits has not established construct validity.

## Participant experience contract

Before the first move is locked:

1. The participant knows their role: they inherited a production system.
2. They know the interaction rule: record what they would actually do first.
3. They are not told what latent failure to look for.
4. Candidate diagnostic actions are absent from the DOM, not merely visually hidden.
5. No correctness feedback appears.

After the first move is locked:

1. The default interface is a free-form investigation console, not a diagnostic menu.
2. The participant writes what they want to inspect, compare, or test.
3. If the request maps to a modeled action, evidence is revealed and budget is charged.
4. If it is not modeled, preserve the request as an instrument limitation rather than a participant error.
5. A secondary **Show available checks** control may reveal the structured menu; opening it is logged.
6. Terminal action and defer are available immediately; investigation is not mandatory.
7. The full event trajectory is recorded locally.
8. Instrument critique occurs only after the task.

This produces an explicit distinction:

- **problem opening:** the participant generates an investigation before candidate actions are supplied;
- **problem recognition:** the participant identifies a useful investigation after choosing to reveal the menu.

These must not be collapsed.

## Interface philosophy

The interface should feel like a restrained production incident console, not a survey and not a game.

Visual quality is part of measurement quality when it reduces confusion about role, state transitions, and available interaction. But visual salience must not encode a diagnosis.

The participant should understand, without external coaching:

`handoff → first move → investigation → decision → critique`

The interface should make those state transitions obvious while leaving the epistemic work to the participant.

## Falsification gates

The environment fails if any of the following survives replication:

1. **Obviousness:** naive participants identify the latent cause from a giveaway rather than inquiry.
2. **Counterfactual insensitivity:** causal twins do not shift investigation behavior.
3. **Surface sensitivity:** cosmetic twins materially shift behavior.
4. **Menu creation:** the key problem appears only after the menu supplies its ontology.
5. **Domain trivia:** performance is explained mainly by specialist vocabulary or memorized platform behavior.
6. **Generic diligence:** a generic strategy such as “check logs” performs nearly as well across all worlds.
7. **Omitted-action failure:** experienced participants repeatedly propose a higher-value action absent from the world model.
8. **Expert incoherence:** blinded experts do not regard the evidence/action consequences as technically coherent.
9. **UI comprehension confound:** first-time participants require experimenter explanation to understand how to participate.
10. **Free-form mapping fragility:** reasonable investigation requests are frequently mis-mapped or rejected because of wording rather than substance.

## Pilot sequence

### Stage A — UX dogfood

Developer-exposed participants may test comprehension, interaction friction, cueing, and event logging. Their responses are not study evidence.

### Stage B — naive instrument pilot

Recruit 5–8 engineers/researchers with ML, data, backend, or production-debugging experience who have not seen the PAJ hypothesis or repository. Give only the URL. Do not recruit only vector-database specialists.

For each session:

1. participant receives one opaque world/rendering;
2. first move is locked before candidate investigations appear;
3. participant first encounters the free-form investigation console;
4. opening the structured menu is optional and logged;
5. participant investigates and terminates at will;
6. participant critiques missing actions and leakage only after termination;
7. two independent coders score the pre-menu response while blind to world, downstream actions, and outcome.

### Stage C — counterfactual validity

Test whether causal twins shift inquiry while surface twins preserve it. Revise the world rather than marking participants wrong when experts expose a better investigation than the benchmark oracle.

### Stage D — AI treatment study

Only after the instrument passes validation introduce randomized assistance history. Preferred first intervention:

- Frame-first: canonical assistance packet appears before self-framing.
- Self-frame-first: participant records a private, non-binding, revisable frame before receiving the exact same packet.

Assisted-task performance is an arm-level design/equivalence gate. Do not match or condition on individual post-treatment performance.

Delayed evaluation removes AI and uses held-out unframed worlds with endogenous information acquisition.

## Interpretation discipline

Do not claim from PAJ-World v1 alone that:

- AI degrades or preserves judgment;
- one assistance sequence is superior;
- PAJ is validated;
- a participant who differs from the oracle is irrational;
- a retrieval-specific effect generalizes to research judgment.

The oracle is an instrument-validation device. Human rationality is not defined by matching its first action.

## Success criterion for this version

The next participant should be able to receive only the URL, understand the task without experimenter coaching, make a genuine first move before the interface supplies candidate diagnoses, propose at least one investigation in their own words, and leave a trajectory whose causal sensitivity can later be tested.

The scientific sequence is deliberate:

**first prove the ruler bends when the world bends; only then use it to measure what AI leaves behind.**
