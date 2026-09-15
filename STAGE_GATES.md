# PAJ-Eval Stage Gates

## Stage 0 — Instrument Skeleton
**Status: CONDITIONAL PASS**

Goal: prove the construct can be represented as an executable sequential decision environment.

Required artifacts:
- causal toy world;
- objective observation model;
- budgeted research actions;
- Expected / Realized Research Utility;
- EIG/cost;
- oracle planner;
- naive baselines;
- deterministic seeded simulation;
- public CI.

Exit rule:
- oracle > sensible heuristic > weak baselines;
- no metric degeneracy;
- oracle first action responds to initial evidence;
- implementation reproducible;
- install and tests pass from public repository.

---

## Stage 1A — Minimal Environment Falsification
**Status: NEXT**

Goal: try to invalidate the instrument before scaling it.

Build:
- one adversarial counterfactual pair;
- two surface renderings per latent world;
- richer observations: plots, logs, sample outputs, notes;
- actions whose value changes with evidence history;
- heuristic attack suite;
- surface-only leakage probe;
- omitted-action capture.

Expert walkthrough:
- 5–8 experienced ML researchers/engineers;
- blinded to latent cause, likelihood tables, EIG, reward parameters, and oracle.

Kill gates:
- similar-looking counterfactual worlds do not produce different investigation priorities;
- same latent world changes qualitatively under superficial rerendering;
- a fixed heuristic approaches oracle;
- superficial wording predicts cause or oracle first action too well;
- experts systematically reject benchmark-preferred moves;
- experts repeatedly identify missing dominant investigations;
- modest reward perturbations reverse the intended action ranking.

Deliverable:
`Stage1A_Falsification_Report.md`

---

## Stage 1B — Environment Validity at Scale

Goal: determine whether PAJ-Eval remains coherent after expanding beyond the hand-built pair.

Build:
- 6–10 causal worlds;
- 2–3 surface renderings where they provide a real invariance test;
- at least 2 held-out mechanism families;
- world generator separated from surface renderer;
- discriminant-validity screens for factual knowledge and Bayesian numeracy.

Primary questions:
- Are multiple hypotheses genuinely plausible?
- Are high-value investigations recognizable as good research?
- Are distractors realistic rather than arbitrary?
- Does any universal heuristic solve most worlds?
- Does score remain informative beyond factual ML knowledge and numeracy?

Acceptance gates:
- median expert realism ≥4/5;
- >1 plausible initial explanation in ≥80% of worlds;
- no universal first move;
- simple heuristics meaningfully below oracle;
- positive expert/benchmark action-value coherence;
- surface invariance;
- counterfactual sensitivity;
- leakage resistance;
- acceptable omitted-action coverage;
- reward robustness;
- evidence of discriminant validity.

Deliverable:
`PAJ-Eval Environment Validity Report v0.2`

---

## Stage 2 — Treatment Validity

Goal: establish a causal manipulation that changes who frames first while keeping eventual AI information as similar as possible.

Preferred design: **information-yoked sequencing**.

Build:
- frozen base model / canonical assistance packets;
- Frame-first protocol;
- Commit-first protocol;
- commitment capture UI;
- treatment-fidelity logger;
- information-overlap audit;
- effort / time / turn logging.

Required manipulation checks:
- independent commitment before AI frame exposure;
- substantive information overlap between arms;
- comparable eventual recommendation exposure;
- stable treatment separation;
- blinded fidelity audit.

Assisted-task performance:
- calibrate arms ex ante to practical equivalence;
- test arm-level equivalence using a preregistered margin;
- **do not condition the treatment-effect analysis on participant-level observed assisted performance.**

Deliverable:
`Sequencing Intervention Validation Report v0.3`

---

## Stage 3 — Human Feasibility Pilot

Goal: establish that delayed, unframed post-assistance measurement is feasible and produces interpretable variance with humans.

Initial target:
- N ≈ 40–60;
- randomized Frame-first vs Commit-first;
- baseline no-AI world;
- 2–3 assisted training worlds;
- delayed no-AI held-out worlds;
- at least one transfer level stronger than pure surface rerendering.

Primary endpoint:
- post-assistance Expected Research Utility / oracle regret.

Secondary:
- Realized Research Utility;
- EIG per budget;
- time to first discriminating investigation;
- frame revision;
- stopping quality.

Purpose:
- feasibility, variance estimation, fidelity, and effect-direction estimation;
- no publication-grade causal claim unless the study is powered and preregistered for it.

Deliverable:
`Human Pilot Report v0.4`

---

## Stage 4 — Confirmatory Study

Goal: test the causal claim under a frozen instrument.

Requirements:
- preregistration;
- simulation-based power analysis;
- held-out worlds frozen before collection;
- primary transfer level chosen in advance;
- blinded scoring / analysis where possible;
- assisted-performance equivalence gate;
- fidelity threshold fixed in advance;
- primary analysis fixed before unblinding;
- null result interpreted as evidence against the stronger treatment hypothesis rather than benchmark failure by default.

Deliverable:
`PAJ-Eval v1.0 Paper + Dataset + Code`

---

## Stage 5 — External / Field Validity

Goal: test whether PAJ-Eval predicts behavior in repeated real AI-assisted work.

Possible settings:
- research workflows;
- coding/debugging;
- data analysis;
- operations diagnosis.

Questions:
- Does lab PAJ predict independent verification and reframing later?
- Does expertise moderate effects?
- Which delegation patterns predict stronger or weaker post-assistance judgment?
- Does an information-ordering intervention that matters in the lab still matter when users can freely choose how to use AI?

Deliverable:
`PAJ-Eval Field Validation`
