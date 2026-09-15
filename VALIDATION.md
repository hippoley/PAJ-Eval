# PAJ-Eval v0.2 — Prototype Validation Notes

## What Stage 0 validates

The current toy world demonstrates that the proposed measurement object can be represented as a non-degenerate sequential decision environment.

Across 300 deterministic simulated episodes per policy:

- **Oracle** achieves the highest Expected Research Utility.
- **Greedy EIG/cost** collects more raw information than the oracle but achieves lower decision utility because it does not optimize stopping and terminal action jointly.
- **Random** investigation performs much worse.
- **Expensive-bias** performs catastrophically despite spending the full budget.

This qualitative ordering is intentional.

The public repository also runs CI. Installation and tests currently pass on the `main` branch.

## Why the Greedy-EIG result matters

The most useful Stage 0 result is not “oracle beats baselines.”

It is this separation:

```text
more information gathered ≠ better research judgment
```

A policy can accumulate high EIG while continuing to investigate after the expected value of additional evidence no longer justifies its cost.

This is why PAJ-Eval separates:

- information acquisition quality,
- stopping quality,
- terminal decision quality.

The expensive `full_retrain` action is deliberately attractive but weakly diagnostic. Cheap targeted diagnostics can dominate it.

## Initial-evidence sensitivity

Episodes begin with noisy visible clues such as:

- slice anomaly;
- metric inconsistency;
- seed variance;
- underfit pattern;
- ambiguous evidence.

These clues induce different objective initial posteriors.

The exact finite-budget oracle already changes its first investigation across these evidence states. In the current toy world, the five clue states produce at least four distinct oracle first-action patterns rather than a single universal move.

A public unit test now protects this property from accidental regression.

## Expected vs realized utility

The implementation already records two distinct quantities:

- `research_utility_expected`: expected terminal reward under the evidence state minus investigation cost;
- `research_utility_realized`: reward under the sampled true cause minus investigation cost.

The v0.2 specification names these **Expected Research Utility (ERU)** and **Realized Research Utility (RRU)**.

ERU is the preferred decision-quality endpoint because it does not reward stochastic luck. RRU remains a useful ecological secondary outcome.

## Reproducibility

The earlier Stage 0 implementation had a subtle source of cross-process nondeterminism: random action selection could depend on Python `set` iteration order.

The public version now sorts candidate actions before seeded random choice and sorts oracle action iteration for deterministic tie-breaking.

A unit test checks seeded RandomPolicy reproducibility.

## What Stage 0 does not validate

This is still a **toy Bayesian world**, not yet a validated human research environment.

Stage 0 does not establish:

1. that humans experience the rendered task as authentic research judgment;
2. that benchmark scores are not reducible to Bayesian numeracy or ML trivia;
3. that surface wording does not leak latent cause;
4. that the action menu includes the investigations experts would actually want;
5. that the reward model agrees with expert scientific judgment;
6. that any AI interaction policy changes later human behavior;
7. that any synthetic-lab effect generalizes to real research workflows.

Those are separate empirical questions.

## Current known structural weaknesses

The toy world still uses:

- hand-authored likelihood tables;
- binary observations;
- a small latent-cause set;
- a closed action menu;
- synthetic costs and terminal rewards;
- no expert-derived calibration.

These are acceptable for an instrument skeleton and unacceptable for a confirmatory human claim.

## Next build target: Stage 1A minimal falsification

The next milestone is not a large benchmark suite.

Build one **adversarial counterfactual pair** with:

- similar visible evidence;
- different latent causal structure;
- different high-value next investigation;
- two substantially different surface renderings per latent world;
- richer research-like artifacts rather than `signal/no_signal`;
- heuristic and leakage attacks;
- 5–8 blinded expert walkthroughs;
- omitted-action capture;
- reward-perturbation analysis.

Only if that small instrument survives should the project scale to a larger world generator.

See:

- [`MEASUREMENT_VALIDITY.md`](MEASUREMENT_VALIDITY.md)
- [`STAGE1_BUILD_BRIEF.md`](STAGE1_BUILD_BRIEF.md)

## Validation philosophy

> **A successful Stage 1 is not one in which PAJ-Eval looks sophisticated. It is one in which the instrument survives attempts to explain its scores with simpler constructs and survives attempts to break its causal distinctions.**
