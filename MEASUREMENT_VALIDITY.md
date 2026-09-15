# PAJ-Eval — Measurement Validity and Kill Tests

## Why this document exists

The central risk in PAJ-Eval is not that the code fails. It is that the benchmark successfully measures the wrong thing.

A synthetic world can be internally elegant while rewarding:

- Bayesian numeracy,
- ML trivia,
- benchmark-pattern recognition,
- action-name matching,
- generic diligence,
- or the benchmark author's own taste.

PAJ-Eval should therefore be treated as **invalid until it survives adversarial measurement tests**.

The goal of Stage 1 is not to maximize benchmark polish. It is to accumulate evidence that the score tracks recognizable research judgment and responds to the distinctions the theory claims it should respond to.

---

## 1. Counterfactual sensitivity

Construct paired worlds with deliberately similar initial surfaces but different latent structures.

Example:

- both worlds show elevated seed variance;
- in World A, optimization instability is the root cause;
- in World B, seed variance is incidental and an evaluation artifact is the root cause.

A valid instrument should assign different value to the next investigation once the full evidence state is considered.

**Kill condition:** the same simple first move remains near-optimal across most counterfactual pairs.

---

## 2. Surface invariance

Render the same latent world through substantially different surface stories.

Examples:

- transformer classification,
- retrieval/ranking,
- vision evaluation,
- recommender experimentation,
- synthetic scientific analysis.

The wording, artifact names, and visual cues may change, but the underlying decision structure does not.

A valid instrument should preserve the relative value of corresponding investigations across renderings.

**Kill condition:** benchmark performance depends strongly on domain nouns, labels, or visual conventions rather than causal structure.

---

## 3. Heuristic resistance

Attack each generated world with deliberately simple policies:

- cheapest action first;
- most expensive action first;
- subgroup analysis first;
- rerun first;
- action-name similarity to visible anomaly;
- fixed investigation sequence;
- greedy EIG/cost;
- stop immediately;
- never stop until budget exhaustion.

Report performance relative to random and oracle baselines.

**Provisional kill condition:** any fixed heuristic remains within 10% of oracle ERU on more than 70% of validated worlds, or a trivial lexical heuristic predicts the oracle first action with high accuracy.

The exact thresholds should be revised after generator-scale simulation rather than defended as theoretically privileged constants.

---

## 4. Latent-cause and action leakage audit

A benchmark can look ambiguous to a human author while leaking the answer through phrasing.

Before participant testing, train or prompt a diagnostic classifier using **only initially visible surface text and metadata** to predict:

1. latent cause;
2. oracle-optimal first action.

Repeat with artifact labels removed or permuted.

If superficial text alone predicts the hidden cause or best first action substantially above what the intended evidence structure supports, rewrite the rendering.

**Important:** this is not a model-performance benchmark. The classifier is a leakage detector.

---

## 5. Expert coherence without oracle worship

Recruit experienced ML researchers/engineers who remain blind to:

- latent cause,
- likelihood tables,
- EIG values,
- oracle policy,
- reward parameters.

Ask them to rank candidate investigations and explain which evidence would most change their view.

Compare:

- rank correlation with benchmark action value;
- top-k overlap;
- agreement on clearly low-value actions;
- disagreement clusters.

The benchmark should not require experts to reproduce the oracle exactly. Experts may value robustness, implementation effort, or scientific norms not encoded in the toy world.

**Kill condition:** experts systematically identify high-value investigations that the benchmark scores as nearly worthless, or repeatedly regard oracle-preferred actions as scientifically indefensible.

Such disagreements require adjudication, not dismissal as “human error.”

---

## 6. Omitted-action audit

A closed action menu can manufacture apparent rationality by excluding what a real researcher would do.

After each walkthrough, ask experts:

> What investigation would you run if you were not constrained by this menu?

Classify proposed actions into:

- semantically equivalent to an existing action;
- useful but missing;
- unrealistic / unavailable under the scenario;
- redundant with already available evidence.

**Kill condition:** experts frequently propose high-value actions outside the menu that would dominate the benchmark's intended choices.

The action set should be revised before human treatment studies.

---

## 7. Reward robustness

Perturb:

- investigation costs,
- wrong-action penalties,
- defer value,
- priors,
- budget,
- terminal reward asymmetry.

Measure whether:

- oracle first-action distribution changes catastrophically;
- policy ranking reverses under small perturbations;
- one action becomes universally dominant.

**Kill condition:** modest, scientifically reasonable parameter changes reverse the benchmark's main distinction between high- and low-quality trajectories.

---

## 8. Discriminant validity

PAJ-Eval should correlate with relevant expertise without collapsing into simpler constructs.

Measure at least:

- factual ML knowledge;
- Bayesian/numeracy screen;
- generic reasoning or planning baseline;
- prior experience debugging ML systems.

Desired pattern:

```text
relevant expertise predicts some PAJ performance,
but PAJ retains substantial residual variance
once factual knowledge and numeracy are accounted for.
```

**Kill condition:** nearly all score variance is explained by a short factual or numeracy test.

---

## 9. Process validity

The construct is a trajectory, so final-answer accuracy alone is insufficient.

For each episode, derive process measures such as:

- first investigation value;
- cumulative expected information gain;
- time/budget before first frame revision;
- response to disconfirming evidence;
- unnecessary evidence collection after a decision is already justified;
- terminal-action quality.

A participant who reaches the right answer through an epistemically poor path should not be indistinguishable from one who made consistently strong choices.

Conversely, stochastic bad luck should not erase evidence of good decisions. This is why Expected Research Utility and Realized Research Utility are reported separately.

---

## 10. Treatment validity for the human study

The preferred first intervention is an **information-yoked sequencing design**.

Both arms eventually receive the same canonical AI information. The key difference is whether the AI frame arrives before or after the participant makes an independent commitment.

Audit:

- information overlap;
- token volume;
- time-on-task;
- commitment compliance;
- direct recommendation exposure;
- participant effort;
- demand-characteristic awareness.

Do not automatically control away effort or self-generation: they may be part of the causal mechanism. Report them and distinguish total-effect from exploratory mechanism analyses.

---

## 11. Transfer ladder

A claim about “post-assistance judgment” should become stronger only as the held-out test becomes more structurally novel.

### T1 — Surface transfer
Same latent structure, different rendering.

### T2 — Mechanism transfer
Held-out latent mechanism family.

### T3 — Compositional transfer
Novel composition of familiar mechanisms.

### T4 — Domain transfer
Different technical domain with homologous decision structure.

A positive effect only at T1 should not be described as general preservation or degradation of research judgment.

---

## 12. Falsification table

| Observation | Interpretation |
|---|---|
| Direct/commit sequencing has no post effect in a validated environment | Stronger treatment hypothesis weakens. |
| Effect disappears after surface change | Likely benchmark-specific learning. |
| Effect survives surface but not mechanism transfer | Some transfer, limited generality. |
| Fixed heuristic approaches oracle | Environment invalid or too narrow. |
| Expert judgments strongly disagree with benchmark value | Scoring/world model requires revision. |
| Effect is explained entirely by information inequality | Treatment invalid for the intended claim. |
| Effect tracks factual ML quiz almost perfectly | Construct collapses toward expertise/knowledge. |
| Effect appears across held-out mechanisms with matched assisted performance and information exposure | Evidence consistent with a genuine post-assistance judgment effect. |

---

## Stage 1 validity principle

> **Do not ask whether PAJ-Eval looks realistic. Ask whether it changes its answer when the underlying causal reason changes, preserves its answer when only the surface changes, and fails when a simpler explanation can account for performance.**

That is the standard the instrument should meet before any strong claim about human–AI interaction policy.
