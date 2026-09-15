# Stage 1 Build Brief — Environment Validity

## Objective

Demonstrate that PAJ-Eval rewards recognizable research judgment rather than exploitation of a small Bayesian game.

Stage 1 is complete only when experienced researchers can inspect rendered environments, remain blind to benchmark likelihood tables, and agree that high-scoring investigation trajectories are substantively better research moves—not merely moves that exploit benchmark conventions.

---

## Stage 1A — Falsification pair first

**Mechanical status: IMPLEMENTED. Human-validity status: NOT YET ESTABLISHED.**

Before expanding the benchmark, build one deliberately adversarial counterfactual pair.

This pair now exists in [`paj_eval/stage1a.py`](paj_eval/stage1a.py):

- both worlds share the same headline anomaly;
- both use the same action menu, costs, observation model, rewards, and budget;
- weak contextual evidence changes the initial evidence state;
- World A's oracle first move is `rerun_seeds`;
- World B's oracle first move is `recompute_metrics`;
- forcing the opposite-world first move incurs >1.0 expected-utility regret in each world.

See [`STAGE1A_COUNTERFACTUAL_PAIR.md`](STAGE1A_COUNTERFACTUAL_PAIR.md).

This is only a **mechanical counterfactual-sensitivity pass**. It is not enough to claim construct validity.

Stage 1A now proceeds to blinded expert walkthroughs using:

- [`EXPERT_WALKTHROUGH_STAGE1A.md`](EXPERT_WALKTHROUGH_STAGE1A.md)
- [`expert_walkthrough_stage1a.html`](expert_walkthrough_stage1a.html)

Do not scale the world generator until this pair survives the human-validity kill gates.

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

A surface story should also be reusable across different latent structures where feasible, so superficial language cannot reveal the answer.

---

## 2. Stage 1B expansion target

Only after Stage 1A survives expert review, expand to **6–10 core causal worlds**.

Each world should have:
- 4–7 plausible latent hypotheses;
- 7–12 available investigations;
- at least 2 attractive but low-value actions;
- at least 1 cheap high-information action that is not visually privileged;
- at least 2 plausible stopping points;
- a terminal intervention set with meaningful downside for acting incorrectly.

At least **2 mechanism families should be held out** from any later training condition.

---

## 3. Surface multiplicity

For each validated causal world, create **2–3 surface renderings**.

Examples:
- transformer classification pipeline;
- retrieval/ranking system;
- vision model evaluation;
- recommendation experiment;
- synthetic scientific analysis.

The same latent logic should not be recognizable from fixed nouns or iconography.

Do not lock a 30-episode target until the first counterfactual pair survives expert validation.

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

Before treatment testing, run heuristic agents:

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

### H7 — Stop immediately
Should fail in worlds where discriminating evidence is worth its cost.

### H8 — Exhaust budget
Should fail in worlds where appropriate stopping dominates additional evidence collection.

Kill expansion if a simple fixed heuristic reaches within **10% of oracle utility on >70% of validated worlds**.

---

## 6. Counterfactual world tests

For selected surface renderings, create paired worlds where weak contextual evidence changes the correct research move.

The initial headline anomaly should remain similar enough that a one-keyword policy cannot succeed.

A good investigator must integrate the evidence state and purchase discriminating evidence rather than pattern-match the headline.

The first implemented pair uses a shared seed-variance headline but flips the preferred first diagnostic between `rerun_seeds` and `recompute_metrics`.

---

## 7. Expert walkthrough protocol

Recruit **5–8 experienced ML researchers/engineers** for Stage 1A.

They receive:
- the four current A/B × rendering scenarios in randomized order;
- no latent-cause list;
- no posterior values;
- no EIG values;
- no oracle trajectory.

Capture:
- top-3 chosen investigations;
- rationale;
- confidence;
- perceived realism;
- number of plausible initial explanations;
- belief-changing evidence;
- omitted investigations;
- leakage concerns.

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
- movement in first-choice distribution across the counterfactual pair;
- rank correlation between expert-perceived investigation value and benchmark action value;
- overlap between expert top-3 actions and benchmark top-3 actions;
- qualitative agreement on low-value distractions;
- disagreement clusters;
- rendering sensitivity within the same latent world.

Desired Stage 1A signal:

- `rerun_seeds` receives materially more support in A than B;
- `recompute_metrics` receives materially more support in B than A;
- alternate surface renderings do not reverse the latent-world effect;
- no systematic case where experts strongly prefer an omitted action that would dominate the menu.

---

## 9. Expertise-discrimination test

The benchmark should correlate with relevant expertise, but not collapse into a factual ML exam.

Add a short independent ML knowledge screen only after the environment itself is credible.

Stage 1 concern if:

```text
PAJ score ≈ factual-knowledge score
```

Desired pattern:

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

Check whether qualitative action rankings survive reasonable changes.

If small reward changes reverse the benchmark's central counterfactual distinction, the instrument is too brittle.

---

## 11. Stage 1 acceptance gates

Advance to treatment-policy work only if all hold:

### G1 — Realism
Median expert realism rating >= 4/5.

### G2 — Ambiguity
Experts report >1 plausible initial explanation in >=80% of scenarios.

### G3 — No universal first move
No action is oracle-optimal first in >50% of validated worlds after expansion.

### G4 — No simple shortcut
Fixed heuristics remain meaningfully below oracle.

### G5 — Expert/action-value coherence
Positive expert-value vs benchmark-value rank correlation in aggregate, without requiring exact oracle imitation.

### G6 — Surface robustness
Same causal world rendered differently yields broadly comparable expert and policy ranking.

### G7 — Counterfactual sensitivity
Paired similar-looking worlds produce different preferred investigations when the causal evidence state changes.

### G8 — Reward robustness
Main action rankings survive reasonable parameter perturbations.

### G9 — Omitted-action coverage
Experts do not repeatedly identify an unlisted investigation that dominates the benchmark menu.

### G10 — Leakage resistance
Surface-only cues do not trivially reveal latent cause or intended action.

---

## Stage 1 deliverables

Stage 1A now has:

1. `paj_eval/stage1a.py`
2. `tests/test_stage1a_pair.py`
3. `STAGE1A_COUNTERFACTUAL_PAIR.md`
4. `EXPERT_WALKTHROUGH_STAGE1A.md`
5. `expert_walkthrough_stage1a.html`

Still required before Stage 1A passes:

6. 5–8 blinded expert responses
7. expert ranking / rendering analysis
8. omitted-action review
9. posterior / reward sensitivity analysis
10. Stage 1A validity decision: pass / revise / kill

Only after that should Stage 1B expand the generator and surfaces.
