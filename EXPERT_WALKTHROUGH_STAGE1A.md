# Stage 1A Expert Walkthrough Protocol

**Purpose:** test whether the first PAJ-Eval counterfactual pair encodes recognizable research judgment rather than benchmark-author preference.

This is an **environment-validity study**, not a test of the assistance-policy hypothesis.

## Participants

Target: **5–8 experienced ML researchers or engineers** who have personally debugged model-training or evaluation failures.

Record only coarse background needed for interpretation:

- years working with ML systems;
- primary role (research / applied research / ML engineering / evaluation / other);
- self-rated familiarity with debugging training and evaluation pipelines (1–5).

Do not require participants to know Bayesian decision theory.

## Blinding

Before completing all scenarios, participants should **not** see:

- latent-cause labels;
- benchmark priors/posteriors;
- signal likelihood tables;
- EIG values;
- oracle values or trajectories;
- the intended A/B distinction.

They may see action costs because investigation budget is part of the task.

## Scenario presentation

Present the four current surface scenarios in randomized order:

- latent world A × classification rendering;
- latent world A × retrieval rendering;
- latent world B × classification rendering;
- latent world B × retrieval rendering.

Use opaque scenario IDs. Do not identify which scenarios share a latent world.

Instruction:

> You inherit this system after an unexpected quality regression. You have 8 investigation-budget units. You are not required to use the whole budget. Based only on the material shown, decide what you would investigate first and why.

## Required response per scenario

1. Rank the **top three investigations** you would buy first.
2. Explain why your first choice is more useful than the alternatives.
3. List the **2–4 causal explanations** you currently consider most plausible.
4. State what result from your first investigation would most change your mind.
5. Confidence that your first investigation is a good use of budget: 0–100.
6. Realism of the scenario: 1–5.
7. Number of genuinely plausible initial explanations: 1, 2, 3, 4, 5+.
8. Name any investigation missing from the menu that you would prefer to run.
9. Flag any wording or artifact that seems to reveal the benchmark author's intended answer.

## Action menu

| Investigation | Cost | Participant-facing description |
|---|---:|---|
| `subgroup_metrics` | 1 | Break core metrics down across data subgroups. |
| `preprocess_audit` | 2 | Inspect transformed examples and preprocessing outputs. |
| `recompute_metrics` | 2 | Recompute evaluation metrics directly from raw predictions or scores. |
| `rerun_seeds` | 2 | Repeat the training/fitting procedure across controlled random seeds. |
| `capacity_sweep` | 4 | Run a small capacity sweep and compare systematic underfit. |
| `raw_sample_audit` | 2 | Inspect targeted raw examples and prediction/score errors. |
| `full_retrain` | 7 | Run an expensive full retraining experiment with several changes. |

Participants may choose **stop / act now** if they believe further investigation is not worth the cost, and should explain what action they would take.

## Primary environment-validity comparisons

Do **not** score exact agreement with the oracle as human accuracy.

Instead report:

### 1. Counterfactual sensitivity

Does the distribution of expert first choices move between latent worlds A and B?

Desired signal:

- `rerun_seeds` is substantially more preferred in A than B;
- `recompute_metrics` is substantially more preferred in B than A.

### 2. Top-3 overlap

For each world, compare expert top-3 investigation rankings with benchmark action-value rankings.

Report overlap and rank correlation descriptively; N is too small for strong inferential claims.

### 3. Surface invariance

Within the same latent world, do classification and retrieval renderings produce broadly similar expert rankings?

Large rendering-driven reversals are a failure signal.

### 4. Omitted-action pressure

Count proposed missing actions. Classify whether each is:

- equivalent to an existing action;
- useful but non-dominating;
- likely to dominate the benchmark menu.

If experienced participants repeatedly identify a dominating omitted action, revise the environment before treatment testing.

### 5. Leakage / obviousness

Record whether experts can infer the intended answer from wording alone or describe the scenario as already diagnosed rather than genuinely ambiguous.

## Reveal phase

Only after all scenarios are complete, show the participant:

- the latent causal families;
- the benchmark's initial posterior assumptions;
- the oracle first move for each world;
- the opposite-world forced-action regret.

Then ask:

1. Is the benchmark-preferred first action scientifically defensible?
2. Is the strength of preference too strong, too weak, or plausible?
3. Which posterior assumption is least credible?
4. Which likelihood assumption is least credible?
5. Does the pair reflect a real distinction you have encountered in practice?
6. What change would make you trust this environment more?

## Pre-specified Stage 1A kill rules

Pause expansion and revise the pair if any of the following occurs:

- a majority of experts reject the benchmark-preferred first action in either world;
- the same first action dominates both worlds despite the intended counterfactual change;
- surface rendering changes expert first-choice ordering more than latent-world identity does;
- participants repeatedly identify one omitted investigation that dominates the current menu;
- median realism is below 4/5;
- most participants report only one plausible explanation at the start;
- wording is repeatedly described as answer-leaking.

These rules are intentionally conservative. Failing Stage 1A is useful evidence that the instrument needs redesign.

## Files

- Counterfactual implementation: [`paj_eval/stage1a.py`](paj_eval/stage1a.py)
- Mechanical validation: [`STAGE1A_COUNTERFACTUAL_PAIR.md`](STAGE1A_COUNTERFACTUAL_PAIR.md)
- Interactive standalone form: [`expert_walkthrough_stage1a.html`](expert_walkthrough_stage1a.html)
- General validity program: [`MEASUREMENT_VALIDITY.md`](MEASUREMENT_VALIDITY.md)
