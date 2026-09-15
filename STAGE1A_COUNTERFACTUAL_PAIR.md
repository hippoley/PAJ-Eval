# Stage 1A Counterfactual Pair — Mechanical Validation

**Status:** mechanical counterfactual-sensitivity and local robustness checks implemented; human validity not yet established.

## Purpose

Stage 1A asks for the smallest environment that can falsify a central PAJ-Eval requirement:

> Similar-looking research situations should sometimes require different next investigations for principled reasons.

If the same fixed move wins everywhere, PAJ-Eval is measuring benchmark convention rather than research judgment.

## The first pair

Both worlds share the same high-level surface anomaly:

> performance fell after a training-stack update, and repeated runs now disagree.

They also share the same action menu, action costs, observation model, terminal rewards, and budget.

What changes is the initial evidence state implied by weak contextual artifacts.

### World A — optimization instability is more plausible

Visible context includes:

- smooth training loss but material seed-to-seed validation variation;
- optimizer-state restoration warnings after the stack update;
- cached prediction arrays themselves differ across reruns;
- evaluation script checksum unchanged;
- no stable subgroup explaining the full regression.

Mechanical fixture posterior:

```text
preprocessing  0.15
evaluation     0.20
optimization   0.55
capacity       0.10
```

Finite-budget oracle first move:

```text
rerun_seeds
```

### World B — evaluation artifact is more plausible

Visible context includes:

- smooth training loss but material displayed metric variation;
- optimizer defaults and restored state hashes stable;
- cached raw predictions/scores effectively identical where dashboard metrics disagree;
- metric aggregation dependency changed in the same stack update;
- no stable subgroup explaining the full regression.

Mechanical fixture posterior:

```text
preprocessing  0.15
evaluation     0.55
optimization   0.20
capacity       0.10
```

Finite-budget oracle first move:

```text
recompute_metrics
```

## Mechanical result

| World | Oracle first action | Oracle expected utility | Forced opposite-world first action | Regret |
|---|---|---:|---|---:|
| A | `rerun_seeds` | 6.158 | `recompute_metrics` | 1.190 |
| B | `recompute_metrics` | 5.970 | `rerun_seeds` | 1.150 |

This is the first executable counterfactual flip in the repository.

It establishes only that the **formal environment** can encode two superficially similar states in which the value of the next investigation changes materially.

It does **not** establish that experienced researchers will interpret the visible artifacts in the way encoded by the benchmark posterior.

## Local robustness checks

The flip is not located at a single knife-edge posterior.

Holding preprocessing at 0.15 and capacity at 0.10, and moving the remaining 0.75 probability mass between evaluation and optimization:

- `recompute_metrics` remains oracle-optimal through optimization posterior 0.30;
- the decision boundary lies between optimization posterior 0.35 and 0.40;
- `rerun_seeds` remains oracle-optimal from optimization posterior 0.40 upward in the tested grid.

The selected fixtures are therefore separated from the local decision boundary:

```text
World A optimization posterior = 0.55
World B optimization posterior = 0.20
```

Automated tests also perturb the costs of both `rerun_seeds` and `recompute_metrics` independently across 1, 2, and 3 budget units. The preferred first action does not flip in either world across that grid.

These are only **local robustness checks**. They do not validate the hand-set likelihood model, priors, or reward matrix against real expert judgment.

## Surface renderings

Each latent world currently has two text renderings:

1. classification / validation-metric framing;
2. retrieval / ranking-metric framing.

The renderings are presentation-only: they do not alter the latent posterior, action model, or oracle decision.

This is a minimal implementation of surface invariance. A real validity claim requires blinded humans to show that alternate renderings preserve perceived decision structure without leaking the latent cause.

## What could still kill this pair?

Reject or revise the pair if any of the following occurs in expert walkthroughs:

- experts regard one world as already diagnosed rather than genuinely ambiguous;
- experts reject `rerun_seeds` as a defensible high-value first diagnostic in World A;
- experts reject `recompute_metrics` as a defensible high-value first diagnostic in World B;
- an unlisted investigation would dominate the offered action menu;
- wording differences reveal benchmark-author intent rather than causal structure;
- experts' action rankings are highly sensitive to cosmetic rerendering;
- broader posterior, likelihood, or reward perturbations reveal substantial brittleness.

## Next required evidence

1. hide all posterior and likelihood values;
2. present both worlds in randomized order;
3. present at least two surface renderings per latent world;
4. collect top-3 investigation rankings and free-text rationale from 5–8 experienced ML researchers/engineers;
5. ask participants to propose any missing investigation they would actually run;
6. only after completion, reveal the causal model/oracle and ask whether its preferred evidence was defensible;
7. run the pre-specified expert-response analysis without selecting metrics after seeing responses.

The criterion is not exact agreement with the oracle. The criterion is whether the benchmark's distinction survives contact with recognizable expert research practice.

## Implementation

- Pair definition: [`paj_eval/stage1a.py`](paj_eval/stage1a.py)
- Counterfactual tests: [`tests/test_stage1a_pair.py`](tests/test_stage1a_pair.py)
- Robustness tests: [`tests/test_stage1a_sensitivity.py`](tests/test_stage1a_sensitivity.py)
- Expert protocol: [`EXPERT_WALKTHROUGH_STAGE1A.md`](EXPERT_WALKTHROUGH_STAGE1A.md)
- Standalone expert form: [`expert_walkthrough_stage1a.html`](expert_walkthrough_stage1a.html)
- Pre-specified analysis: [`analyze_stage1a_experts.py`](analyze_stage1a_experts.py)
- Broader validity gates: [`MEASUREMENT_VALIDITY.md`](MEASUREMENT_VALIDITY.md)
- Tracking issue: [#2 — Stage 1A counterfactual pair](https://github.com/hippoley/PAJ-Eval/issues/2)
