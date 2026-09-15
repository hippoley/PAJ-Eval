# Stage 1A Counterfactual Pair — Mechanical Validation

**Status:** mechanical counterfactual-sensitivity check implemented; human validity not yet established.

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

Examples of visible context:

- smooth training loss but material seed-to-seed validation variation;
- optimizer-state restoration warnings after the stack update;
- cached prediction arrays themselves differ across reruns;
- evaluation script checksum is unchanged;
- no stable subgroup explains the full regression.

Initial benchmark posterior used by the mechanical fixture:

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

Examples of visible context:

- smooth training loss but material displayed metric variation;
- optimizer defaults and restored state hashes are stable;
- cached raw predictions/scores are effectively identical where dashboard metrics disagree;
- metric aggregation dependency changed in the stack update;
- no stable subgroup explains the full regression.

Initial benchmark posterior used by the mechanical fixture:

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

Using the Stage 1A fixture:

| World | Oracle first action | Oracle expected utility | Forced opposite-world first action | Regret |
|---|---|---:|---|---:|
| A | `rerun_seeds` | 6.158 | `recompute_metrics` | 1.190 |
| B | `recompute_metrics` | 5.970 | `rerun_seeds` | 1.150 |

This is the first executable counterfactual flip in the repository.

It establishes only that the **formal environment** can encode two superficially similar states in which the value of the next investigation changes materially.

It does **not** establish that experienced researchers will interpret the visible artifacts in the way encoded by the benchmark posterior.

## Surface renderings

Each latent world currently has two text renderings:

1. classification / validation-metric framing;
2. retrieval / ranking-metric framing.

The renderings are presentation-only: they do not alter the latent posterior, action model, or oracle decision.

This is a minimal implementation of surface invariance. A real validity claim requires blinded humans to show that alternate renderings preserve perceived decision structure without leaking the latent cause.

## What could still kill this pair?

The pair should be rejected or revised if any of the following occur in expert walkthroughs:

- experts regard one world as obviously solved from the visible artifacts rather than genuinely ambiguous;
- experts do not agree that `rerun_seeds` is a defensible high-value first diagnostic in World A;
- experts do not agree that `recompute_metrics` is a defensible high-value first diagnostic in World B;
- an unlisted investigation would dominate the offered action menu;
- wording differences reveal the benchmark-author intent rather than the causal structure;
- experts' action rankings are highly sensitive to cosmetic rerendering;
- modest changes to the hand-set initial posterior reverse the pair too easily.

## Next required evidence

The mechanical pair is ready for the next, much harder gate:

1. hide all posterior and likelihood values;
2. present both worlds in randomized order;
3. present at least two surface renderings per latent world;
4. collect top-3 investigation rankings and free-text rationale from 5–8 experienced ML researchers/engineers;
5. ask participants to propose any missing investigation they would actually run;
6. only after completion, reveal the benchmark model and ask whether its preferred evidence was defensible.

The criterion is not exact agreement with the oracle. The criterion is whether the benchmark's distinction survives contact with recognizable expert research practice.

## Implementation

- Pair definition: [`paj_eval/stage1a.py`](paj_eval/stage1a.py)
- Tests: [`tests/test_stage1a_pair.py`](tests/test_stage1a_pair.py)
- Broader validity gates: [`MEASUREMENT_VALIDITY.md`](MEASUREMENT_VALIDITY.md)
- Tracking issue: [#2 — Stage 1A counterfactual pair](https://github.com/hippoley/PAJ-Eval/issues/2)
