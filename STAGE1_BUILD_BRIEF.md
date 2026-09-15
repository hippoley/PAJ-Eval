# Stage 1 Build Brief — Environment Validity

## Objective

Demonstrate that PAJ-Eval rewards recognizable research judgment rather than exploitation of a small Bayesian game.

The revised execution principle is:

> **Do not build 30 polished episodes before we know the instrument survives one hard counterexample.**

Stage 1 is therefore split into **Stage 1A: Minimal Falsification** and **Stage 1B: Scale Validation**.

---

# Stage 1A — Minimal Falsification

## 1. Build one adversarial counterfactual pair

Create two research environments with intentionally similar initial evidence but different latent causal structures.

Example:

### World A
Visible evidence includes elevated seed variance, mild subgroup drift, and a suspicious preprocessing note. The true cause is **optimization instability**.

### World B
The same visible motifs appear, but seed variance is incidental and the true cause is an **evaluation artifact** or **conditional preprocessing mismatch**.

The key requirement is not that the root causes differ. It is that **the best next investigation differs for principled reasons**.

If the same obvious action remains best in both worlds, rebuild the pair.

## 2. Render each world twice

Use at least two substantially different surface renderings for the same latent structure.

Initial target:

```text
2 latent worlds × 2 surface renderings = 4 episodes
```

This is enough to test the two most important invariances:

- **counterfactual sensitivity:** change latent reason → preferred investigation changes;
- **surface invariance:** change surface story → underlying action values remain coherent.

Do not scale until both are visible.

## 3. Replace binary observations in the pair

The first adversarial pair should already expose research-like evidence:

- metric tables,
- small plots,
- logs,
- subgroup slices,
- seed distributions,
- sample-level errors,
- confidence intervals,
- partial failures.

The internal scoring model may discretize these artifacts, but participants should not see `signal/no_signal` abstractions.

## 4. Heuristic attack suite

Run at least:

- cheapest-first;
- expensive-first;
- subgroup-first;
- rerun-first;
- fixed sequence;
- anomaly/action-name lexical match;
- greedy EIG/cost;
- stop-immediately;
- exhaust-budget.

Also run a **surface-only leakage probe** that sees the initial wording and labels but cannot purchase evidence. Ask it to predict:

1. latent cause;
2. oracle first action.

A good pair should resist both fixed heuristics and superficial leakage.

## 5. Expert walkthrough before expansion

Recruit **5–8 experienced ML researchers/engineers** for the four Stage 1A episodes.

Keep them blind to:

- latent cause;
- likelihood tables;
- EIG values;
- oracle policy;
- reward parameters.

Capture:

- first investigation;
- ranked top-3 investigations;
- rationale;
- confidence;
- perceived realism;
- initial plausible explanations;
- what evidence would change their mind;
- any missing investigation they would run in real work.

After completion, reveal the world model and oracle and ask whether benchmark-preferred actions reflect good research or game logic.

## 6. Stage 1A kill gates

Do **not** proceed to large-scale generation if any of these fail materially:

### K1 — Counterfactual sensitivity
The two similar-looking worlds do not require meaningfully different investigation priorities.

### K2 — Surface invariance
Experts or policies change dramatically when only nouns/rendering change.

### K3 — Heuristic resistance
A fixed heuristic approaches oracle across the pair.

### K4 — Leakage
The latent cause or oracle first action is easily predicted from superficial wording alone.

### K5 — Expert coherence
Experts repeatedly regard the benchmark-preferred action as scientifically poor.

### K6 — Omitted-action coverage
Experts identify missing actions that would clearly dominate the available menu.

### K7 — Reward robustness
Small plausible changes in costs/rewards reverse the intended action ranking.

If a kill gate fails, revise the world/scoring model before adding more content.

---

# Stage 1B — Scale Validation

Only after Stage 1A survives should the project expand.

## 7. World generator architecture

Separate:

```text
Causal World Generator
        ↓
Observation / Experiment Model
        ↓
Surface Renderer
        ↓
Research Interface + Event Logger
```

A causal world must be renderable through multiple surface stories without changing its latent decision structure.

A surface story should also be reusable across different latent structures so superficial nouns cannot reliably reveal the answer.

## 8. Scale target

Expand to **6–10 core causal worlds**, not automatically 30.

Each world should have:

- 4–7 plausible latent hypotheses;
- 7–12 investigations;
- ≥2 attractive but low-value actions;
- ≥1 cheap high-information action that is not visually privileged;
- ≥2 plausible stopping points;
- meaningful downside to incorrect terminal action.

Use **2–3 surface renderings per world** only where they provide a real invariance test.

At least **2 mechanism families** should be held out from the assisted training condition for later transfer measurement.

## 9. Mechanism-family target

The v0.2 generator should support at least:

- conditional preprocessing mismatch;
- evaluation implementation artifact;
- optimization instability;
- capacity mismatch;
- conditional label corruption;
- leakage / spurious shortcut.

Later worlds may compose more than one mechanism, but single-cause worlds remain useful for calibration and interpretability.

## 10. Expert validation at scale

Do not require experts to copy the exact oracle.

Measure:

- rank correlation between expert-perceived action value and benchmark value;
- top-3 overlap;
- qualitative agreement on low-value distractions;
- disagreement clusters;
- frequency of missing-action proposals;
- realism and ambiguity ratings.

Desired pattern:

```text
benchmark value and expert judgment are positively related,
but disagreement remains where real research judgment is genuinely contestable.
```

## 11. Discriminant validity

Add independent screens for:

- factual ML knowledge;
- Bayesian/numeracy skill;
- ML debugging experience.

The benchmark should be expertise-sensitive without collapsing into a knowledge exam.

Concern:

```text
PAJ ≈ factual quiz
```

Desired:

```text
expertise matters,
but investigation quality retains residual variance.
```

## 12. Reward robustness

Perturb:

- costs;
- priors;
- wrong-action penalties;
- defer reward;
- total budget;
- terminal reward asymmetry.

Track whether world difficulty and policy ranking remain stable enough to support interpretation.

---

# Stage 1 acceptance gates

Advance to a human treatment pilot only if the validated world set satisfies all of the following:

### G1 — Realism
Median expert realism rating ≥ 4/5.

### G2 — Genuine initial ambiguity
More than one plausible initial explanation is reported in ≥80% of worlds.

### G3 — No universal first move
No action is oracle-optimal first in >50% of generated worlds.

### G4 — No simple shortcut
Fixed heuristics remain meaningfully below oracle.

### G5 — Expert coherence
Benchmark action value is positively related to expert-perceived action value.

### G6 — Surface invariance
Alternate renderings of the same latent world preserve qualitative action-value structure.

### G7 — Counterfactual sensitivity
Similar-looking worlds with changed latent structure require different high-value investigations.

### G8 — Leakage resistance
Superficial wording alone does not reliably reveal hidden cause or best first action.

### G9 — Omitted-action coverage
Experts do not frequently identify clearly dominant investigations absent from the menu.

### G10 — Reward robustness
Main conclusions survive reasonable parameter perturbations.

### G11 — Discriminant validity
PAJ performance is not reducible to factual ML knowledge or numeracy alone.

---

# Stage 1 deliverables

## Stage 1A

1. `counterfactual_pair/`
2. `4 rendered episodes`
3. `heuristic_attack_report.csv`
4. `leakage_probe_report.md`
5. `expert_walkthrough_protocol.md`
6. `expert_stage1a_results.csv`
7. `Stage1A_Falsification_Report.md`

## Stage 1B

1. `world_generator/`
2. `renderers/`
3. `6–10 validated causal worlds`
4. `heuristic_baseline_report.csv`
5. `surface_invariance_report.md`
6. `reward_robustness_report.md`
7. `expert_validity_results.csv`
8. `Environment_Validity_Report_v0.2.md`

Only after Stage 1A/1B pass should the project run the information-yoked **Frame-first vs Commit-first** treatment pilot.
