# Reproducibility

PAJ-Eval Stage 0 is deterministic given the supplied seeds.

## Environment

- Python: 3.9+
- Package install: `python -m pip install -e .`
- Test command: `pytest -q`
- Simulation command: `python demo.py`

## Determinism fix in this public release

The original internal prototype selected available actions from Python `set` objects. Although the random number generator itself was seeded, cross-process set iteration order could change the candidate list and therefore change the RandomPolicy trace. Oracle tie-breaking could also inherit set iteration order in exact ties.

The public version stabilizes both paths:

- `RandomPolicy` samples from `sorted(unused)`;
- the oracle iterates `sorted(unused)`.

With those changes, repeated fresh-process runs produce identical `policy_summary.csv` and `policy_simulation.csv` hashes for the fixed demo seed.

## Current deterministic Stage 0 summary

300 episodes per policy, seed = 7:

| Policy | Expected RU | Realized RU | Cost | EIG | IAE | Steps |
|---|---:|---:|---:|---:|---:|---:|
| oracle | 4.417 | 4.567 | 3.593 | 0.759 | 0.214 | 1.710 |
| greedy_eig | 3.442 | 3.750 | 5.310 | 0.925 | 0.190 | 2.537 |
| random | 0.295 | 0.457 | 5.027 | 0.448 | 0.077 | 2.063 |
| expensive_bias | -4.567 | -4.400 | 8.000 | 0.195 | 0.024 | 2.000 |

These numbers are sanity checks for the toy environment, not human-study results.
