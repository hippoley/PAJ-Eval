# PAJ-Eval Validation Status

## Stage 0 — executable instrument

The original toy world separates several qualitatively different research policies.

Across 300 deterministic simulated episodes per policy:

- **Oracle** achieves the highest expected Research Utility.
- **Greedy EIG/cost** gathers more raw information than the oracle but remains below it on Research Utility because it ignores stopping and terminal-value tradeoffs.
- **Random** performs much worse.
- **Expensive-bias** performs catastrophically despite spending the full budget.

This establishes only that the environment is non-degenerate and does not automatically reward more activity.

## Stage 1A — first counterfactual pair

A first adversarial pair is now implemented.

Both worlds share the same headline anomaly and the same action menu, costs, observation model, rewards, and budget. Weak contextual evidence changes which causal family is most plausible.

Mechanical result:

| World | Oracle first action | Oracle expected utility | Forced opposite-world action | Regret |
|---|---|---:|---|---:|
| A | `rerun_seeds` | 6.158 | `recompute_metrics` | 1.190 |
| B | `recompute_metrics` | 5.970 | `rerun_seeds` | 1.150 |

Public CI currently passes **11 tests**, including:

- posterior normalization;
- non-negative EIG;
- oracle validity;
- deterministic Stage 0 behavior;
- identical headline anomaly across the A/B counterfactual pair;
- oracle first-action flip across the pair;
- material regret from copying the other world's first move;
- invariant latent state across alternate surface renderings.

See [`STAGE1A_COUNTERFACTUAL_PAIR.md`](STAGE1A_COUNTERFACTUAL_PAIR.md).

## What this does not validate

The Stage 1A result is **mechanical**, not yet psychological or ecological.

The hand-set initial evidence state may fail to match how experienced researchers interpret the visible artifacts. The pair may also contain wording leakage, omitted actions, unrealistic likelihood assumptions, or reward brittleness.

Therefore PAJ-Eval does **not** yet claim that:

- the counterfactual pair measures real research judgment;
- experts will rank the same first investigations as the benchmark;
- the surface renderings are behaviorally invariant;
- the benchmark is robust to reasonable posterior or reward perturbations;
- the information-yoked treatment changes human post-assistance judgment.

## Next validation gate

Run **5–8 blinded expert walkthroughs** using:

- [`EXPERT_WALKTHROUGH_STAGE1A.md`](EXPERT_WALKTHROUGH_STAGE1A.md)
- [`expert_walkthrough_stage1a.html`](expert_walkthrough_stage1a.html)

Experts should see only participant-facing artifacts, action descriptions, and costs—not posterior values, likelihood tables, EIG, or oracle trajectories.

The key questions are:

1. Does first-choice preference move from `rerun_seeds` toward `recompute_metrics` across A → B?
2. Do alternate renderings preserve the latent-world effect?
3. Are both worlds initially ambiguous enough to require investigation?
4. Do experts identify a missing action that dominates the menu?
5. Do experts regard the benchmark-preferred first actions as scientifically defensible after reveal?

Failing these checks should trigger redesign rather than reinterpretation.

## Validation philosophy

PAJ-Eval should distinguish three very different events:

1. **A treatment hypothesis fails:** the environment is valid but Frame-first and Self-frame-first produce no post-assistance difference.
2. **A particular world fails:** experts reject its artifacts, action menu, posterior assumptions, or reward structure.
3. **The construct fails:** across credible environments, the proposed measurement cannot be separated from known-skill transfer, factual expertise, benchmark literacy, or generic numeracy.

Only the third threatens the research program itself. The first two are useful empirical outcomes.
