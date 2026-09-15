# Reproducibility

## Environment

Reference CI environment:

- Ubuntu 24.04
- Python 3.11
- install: `python -m pip install -e .`
- test: `pytest -q`

The public GitHub Actions workflow checks installation and tests on every push / pull request.

## Current test status

As of 2026-09-15, public CI reports:

```text
11 passed
```

The test suite includes both the original Stage 0 toy-world checks and Stage 1A counterfactual-pair checks.

## Determinism

The prototype uses explicit `random.Random(seed)` instances for simulations.

Action iteration that can affect policy selection or oracle tie-breaking is sorted before selection. This avoids cross-process variation caused by Python set iteration order.

Stage 0 reference simulation:

```bash
python demo.py
```

uses 300 episodes per policy with fixed seed 7.

Reference qualitative ordering:

```text
Oracle > Greedy EIG/cost > Random > Expensive-bias
```

Reference mean expected Research Utility:

```text
Oracle          4.417
Greedy EIG      3.442
Random          0.295
Expensive-bias -4.567
```

## Stage 1A counterfactual fixture

The first counterfactual pair is deterministic at the normative-model level.

Reference first decisions:

```text
World A -> rerun_seeds
World B -> recompute_metrics
```

Reference expected utilities and cross-world forced-action regret:

```text
World A oracle value                  6.158
World A force recompute_metrics       regret 1.190

World B oracle value                  5.970
World B force rerun_seeds             regret 1.150
```

These values are test-fixture results, not empirical human estimates.

## Important boundary

Reproducing the code does not reproduce construct validity.

The initial posteriors and likelihood tables in Stage 1A are hand-specified hypotheses about the decision structure. They must still be challenged by expert walkthroughs, omitted-action review, leakage checks, and sensitivity analysis before they can support a human study.
