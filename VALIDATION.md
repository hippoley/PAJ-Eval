# PAJ-Eval v0.1 — Prototype Validation Notes

## What has been validated so far

The current toy world already separates several qualitatively different research policies.

Across 300 simulated episodes per policy:

- **Oracle** achieves the highest expected Research Utility.
- **Greedy EIG/cost** performs well but remains measurably below the oracle because it ignores stopping and terminal reward tradeoffs.
- **Random** investigation performs much worse.
- **Expensive-bias** performs catastrophically despite spending the full budget.

This is the intended qualitative ordering.

## Why this matters

The environment is not rewarding “more experiments.” It rewards experiments that change the hypothesis space enough to justify their cost.

The expensive `full_retrain` action is deliberately attractive but weakly diagnostic. Cheap targeted diagnostics can dominate it.

## Initial evidence

Episodes now begin with a noisy initial research clue such as:

- slice anomaly;
- metric inconsistency;
- seed variance;
- underfit pattern;
- ambiguous evidence.

The benchmark converts this into an objective initial posterior over latent causes.

This prevents the world from always beginning from the same uniform state and is intended to make the best first experiment depend on evidence already visible in the environment.

## Current limitations

This is still a **toy Bayesian world**, not yet a human study environment.

Major missing pieces:

1. realistic surface artifacts (plots, logs, sample outputs);
2. multiple surface renderings of the same causal world;
3. treatment-policy implementation for Direct vs Elicitation assistance;
4. participant-facing interface;
5. delayed held-out worlds;
6. preregistration and confirmatory power analysis.

## Next build target

The next milestone should be a **single realistic ML research episode** rendered from the causal world:

- a small dashboard;
- 8–12 visible artifacts;
- evidence revealed only after chosen investigations;
- budget tracking;
- hypothesis/confidence snapshots;
- terminal intervention;
- complete event log.

That would be the first version suitable for expert walkthroughs.
