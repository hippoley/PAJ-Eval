# Stage 1 Build Brief — Environment Validity

## Objective

Demonstrate that PAJ-Eval rewards recognizable research judgment rather than exploitation of a small Bayesian game.

Stage 1 is complete only when an experienced researcher can inspect the rendered environments, remain blind to benchmark likelihood tables, and agree that high-scoring investigation trajectories are substantively better research moves—not merely moves that exploit benchmark conventions.

---

## 1. Architecture change

Separate four layers:

```text
Causal World Generator
        ↓
Observation / Experiment Model
        ↓
Surface Renderer
        ↓
Research Interface + Event Logger
```

A causal world must be renderable through multiple surface stories without changing its latent structure.

A surface story must also be reusable across different latent structures where possible, so that superficial language cannot reveal the answer.

---

## 2. World count

Build **10 core causal worlds**.

Each world should have:
- 4–7 plausible latent hypotheses;
- 7–12 available investigations;
- at least 2 attractive but low-value actions;
- at least 1 cheap high-information action that is not visually privileged;
- at least 2 plausible stopping points;
- a terminal intervention set with meaningful downside for acting incorrectly.

At least **2 mechanism families are held out** from any later training condition.

---

## 3. Surface multiplicity

For each causal world, create **3 surface renderings**.

Examples:
- transformer classification pipeline;
- retrieval/ranking system;
- vision model evaluation;
- recommendation experiment;
- synthetic scientific analysis.

The same latent logic should not be recognizable from fixed nouns or iconography.

Target:

```text
10 causal worlds × 3 renderings = 30 rendered episodes
```

---

## 4. Observation richness

Replace binary `signal/no_signal` where feasible with richer outputs:

- small numeric tables;
- metric deltas;
- mini-plots;
- sample-level errors;
- logs;
- confidence intervals;
- seed-to-seed variability;
- subgroup differences;
- partial failures.

The benchmark may internally discretize these for posterior calculation, but participants should encounter research-like artifacts.

---

## 5. Anti-shortcut tests

Before human testing, run heuristic agents:

### H1 — Always choose cheapest action
Should not approach oracle performance.

### H2 — Always choose subgroup analysis first
Should fail meaningfully on some worlds.

### H3 — Always choose the action whose name best matches the initial anomaly
Should not dominate.

### H4 — Always use the same fixed sequence
Should incur substantial oracle regret.

### H5 — Expensive-action preference
Should remain clearly suboptimal.

### H6 — Greedy EIG
Should be strong but not identical to the full oracle because stopping and terminal value matter.

Kill Stage 1 if any simple fixed heuristic reaches within **10% of oracle utility on >70% of worlds**.

---

## 6. Counterfactual world tests

For selected surface renderings, create paired worlds where one hidden parameter changes the correct research move.

Example:

- World A: seed instability is the root cause.
- World B: the same visible seed variance is incidental; evaluation leakage is the root cause.

The initial surface should look similar.

A good investigator must purchase discriminating evidence rather than pattern-match the visible clue.

This is one of the most important Stage 1 tests.

---

## 7. Expert walkthrough protocol

Recruit **5–8 experienced ML researchers/engineers**.

They receive:
- 4–6 rendered worlds each;
- no latent-cause list;
- no EIG values;
- no oracle trajectory.

Capture:
- chosen investigations;
- rationale;
- confidence;
- perceived realism;
- perceived ambiguity;
- whether another expert could reasonably choose differently;
- whether any action label leaks the intended diagnosis.

After completion, reveal the causal model and oracle trajectory.

Ask:

1. Was the benchmark's preferred evidence actually useful?
2. Were low-value distractors realistically tempting?
3. Did the optimal trajectory feel like good research rather than game logic?
4. Which actions were missing?
5. Which artifacts were implausible?
6. Did the reward function punish any defensible scientific behavior?

---

## 8. Human-expert agreement target

Do not require experts to copy the exact oracle.

Measure instead:
- rank correlation between expert-perceived investigation value and benchmark EIG/cost;
- overlap between expert top-3 actions and benchmark top-3 actions;
- qualitative agreement on low-value distractions;
- disagreement clusters.

Desired Stage 1 signal:

- positive rank correlation across worlds;
- no systematic case where experts strongly prefer actions the benchmark labels nearly worthless;
- disagreements are explainable by genuine uncertainty rather than artifact flaws.

---

## 9. Expertise-discrimination test

The benchmark should correlate with relevant expertise, but not collapse into a factual ML exam.

Add a short independent ML knowledge screen.

Stage 1 concern if:

```text
PAJ score ≈ factual-knowledge score
```

Stage 1 desired pattern:

```text
expertise matters,
but investigation quality retains substantial residual variance.
```

---

## 10. Reward robustness

Perturb:
- investigation costs;
- false-intervention penalties;
- defer reward;
- prior over latent causes.

Check whether the qualitative ranking of good and bad strategies is robust.

If small reward changes reverse most benchmark conclusions, the instrument is too brittle.

---

## 11. Stage 1 acceptance gates

Advance to treatment-policy work only if all hold:

### G1 — Realism
Median expert realism rating >= 4/5.

### G2 — Ambiguity
Experts report >1 plausible initial explanation in >=80% of worlds.

### G3 — No universal first move
No action is oracle-optimal first in >50% of generated worlds.

### G4 — No simple shortcut
Fixed heuristics remain meaningfully below oracle.

### G5 — Expert/EIG coherence
Positive expert-value vs benchmark-value rank correlation in aggregate.

### G6 — Surface robustness
Same causal world rendered differently yields comparable policy ranking.

### G7 — Counterfactual sensitivity
Paired similar-looking worlds produce different optimal investigations when the latent structure changes.

### G8 — Reward robustness
Main policy ranking survives reasonable parameter perturbations.

---

## Stage 1 deliverables

1. `world_generator/`
2. `renderers/`
3. `30 rendered episodes`
4. `heuristic_baseline_report.csv`
5. `counterfactual_pair_report.md`
6. `expert_walkthrough_protocol.md`
7. `expert_validity_results.csv`
8. `Environment Validity Report v0.2`

Only after these exist should Direct-vs-Elicitation treatment implementation begin.
