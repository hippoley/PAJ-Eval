# PAJ-Eval Stage Gates

## Stage 0 — Instrument Skeleton
**Status: CONDITIONAL PASS**

Goal: prove the construct can be represented as an executable decision environment.

Required artifacts:
- causal toy world
- objective observation model
- budgeted research actions
- Research Utility
- EIG/cost
- oracle planner
- naive baselines
- reproducibility tests

Exit rule:
- oracle > sensible heuristic > weak baselines
- no metric degeneracy
- implementation reproducible

---

## Stage 1 — Environment Validity
**Status: NEXT**

Goal: determine whether the benchmark rewards recognizable research judgment rather than toy-game exploitation.

Build:
- 8–12 generated causal worlds
- 2–3 surface renderings per causal world
- at least 2 held-out mechanism families
- richer observations: plots, logs, sample outputs, notes
- actions whose value changes with evidence history
- world generator separated from surface renderer

Expert walkthrough:
- 5–8 experienced ML researchers
- blinded to latent cause and EIG tables

Primary questions:
- Are multiple hypotheses genuinely plausible?
- Are high-value investigations recognizable as good research after the fact?
- Are distractors realistic rather than arbitrary?
- Does any universal heuristic solve most worlds?
- Is score strongly but not completely associated with expertise?

Kill gates:
- one action dominates >60% of worlds
- experts find artifacts unrealistic
- non-experts with benchmark familiarity outperform experts
- score is >80% explained by factual ML quiz performance

Deliverable:
`PAJ-Eval Environment Validity Report v0.2`

---

## Stage 2 — Treatment Validity

Goal: prove Direct and Elicitation are genuinely different interaction policies while current assisted performance remains approximately matched.

Build:
- frozen base model
- Direct policy protocol
- Elicitation policy protocol
- rescue ladder
- turn-level treatment-fidelity classifier
- information-volume audit

Required manipulation checks:
- frame-before-user rate
- user-generated hypotheses before first supplied frame
- direct recommendation rate
- rescue rate

Gate:
- assisted Research Utility equivalent within preregistered margin
- treatment-fidelity separation large and stable

Deliverable:
`Assistant Policy Validation Report v0.3`

---

## Stage 3 — Human Feasibility Pilot

Goal: establish that delayed, unframed post-assistance measurement works with humans.

Target:
- N ≈ 48
- randomized Direct vs Elicitation
- baseline no-AI world
- 3 assisted training worlds
- delayed no-AI held-out worlds

Primary endpoint:
- post-assistance Research Utility / oracle regret

Mechanism:
- EIG per budget

No publication-grade causal claim unless powered accordingly.

Deliverable:
`Human Pilot Report v0.4`

---

## Stage 4 — Confirmatory Study

Goal: test the causal claim.

Requirements:
- preregistration
- simulation-based power analysis
- held-out worlds frozen before collection
- blinded analysis where possible
- equivalence test on assisted performance
- primary analysis fixed in advance

Deliverable:
`PAJ-Eval v1.0 Paper + Dataset + Code`

---

## Stage 5 — External / Field Validity

Goal: test whether PAJ-Eval predicts real behavior in repeated AI-assisted work.

Possible settings:
- real research workflows
- coding/debugging
- data analysis
- operations diagnosis

Questions:
- Does lab PAJ predict independent verification and reframing later?
- Does expertise moderate effects?
- Which patterns of delegation predict stronger/weaker post-assistance judgment?

Deliverable:
`PAJ-Eval Field Validation`
