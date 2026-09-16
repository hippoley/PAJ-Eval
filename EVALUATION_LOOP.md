# Evaluation Loop

Probe Player is not the evaluator. It is the behavioral surface that produces auditable event traces.

```text
participant in micro-world
        ↓
raw event trajectory
        ↓
pre-specified behavioral features
        ↓
construct measurement
        ↓
validated task score
        ↓
causal / surface validity checks
        ↓
transfer without AI
        ↓
comparison between assistance policies
```

## 1. Raw trajectory

Facts only: which world objects were available, which were opened, order, timing, evidence actually exposed, revisions, stopping, and terminal commitment. The raw trace should not contain hidden semantic labels that would make later coding circular.

## 2. Behavioral features

Examples include spontaneous diagnostic opening before menus, first fixation, evidence diversity, discriminating-test selection, posterior-consistent revision, investigation cost, stopping threshold, and whether a participant opens an object that was not foregrounded.

Features are hypotheses about useful observables. They require reliability and discriminant-validity checks; generic diligence, reading speed, domain trivia, and interface familiarity are rival explanations.

## 3. Construct

The broader construct is independent post-assistance judgment formation: noticing, problem construction, competing frames, evidence acquisition, revision, stopping, and commitment after assistance is absent and the next problem is unframed.

PF01-PF08 each expose only a slice of this construct.

## 4. Score

Where a synthetic world has known latent ground truth, PAJ can compute normative decision quantities such as Expected Research Utility, realized utility, regret, information value, and calibration. SDO can capture spontaneous problem opening before candidate investigations are supplied. Which score is primary depends on the preregistered study stage.

## 5. Counterfactual validity

Causal twins change the latent world enough that a useful investigation/action should change while preserving much of the surface. Surface variants change wording/layout without changing the latent world. A credible instrument should be sensitive to the former and comparatively invariant to the latter.

## 6. Treatment effect

The target comparison is not whether one participant got a prettier trajectory. It is whether assistance policies that achieve equivalent assisted-task performance leave systematically different no-AI judgment on held-out, unframed transfer worlds.

The current clean candidate treatment is information-yoked sequencing: Frame-first versus Self-frame-first with the same eventual assistance packet. Assisted-task equivalence is an arm-level design gate. The causal endpoint is measured after assistance is removed.

## What Probe Player must never claim

A single session does not establish learning, transfer, persistence, human agency, or a treatment effect. The player may visualize how a trace enters the measurement pipeline, but validated claims require the corresponding experimental design and stage gates.