# Contributing to PAJ-Eval

The most useful contribution is not “more scenarios.” It is a concrete way to make the measurement fail.

## Highest-value contributions right now

### 1. Expert walkthroughs

If you have substantial experience debugging ML training or evaluation pipelines, run the Stage 1A walkthrough before reading the latent model:

- protocol: [`EXPERT_WALKTHROUGH_STAGE1A.md`](EXPERT_WALKTHROUGH_STAGE1A.md)
- standalone form: [`expert_walkthrough_stage1a.html`](expert_walkthrough_stage1a.html)

The useful output is not agreement. It is a defensible disagreement with the benchmark's preferred investigation, a missing action, or evidence that a rendering leaks the answer.

### 2. Construct attacks

Examples:

- show that the task reduces to ML trivia or Bayesian numeracy;
- find a fixed heuristic that approaches oracle utility;
- demonstrate that alternate surface wording reverses expert choices;
- identify a scientifically defensible action the benchmark punishes;
- show that the hand-set posterior is not credible given the visible artifacts.

### 3. Counterfactual worlds

A useful new world pair should preserve a similar headline anomaly while changing the value of the next investigation for a principled causal reason.

Do not create difficulty by hiding decision-relevant information from the participant.

### 4. Treatment-design attacks

For the v0.2 information-yoked sequencing intervention, useful critiques include:

- ways Frame-first and Self-frame-first still differ besides causal order;
- effort or consistency-pressure confounds;
- failures of assistance-packet equivalence;
- demand characteristics;
- reasons arm-level assisted equivalence would be insufficient.

## Research norms

PAJ-Eval should be easy to falsify.

Please prefer:

- explicit counterexamples over vague objections;
- reproducible failure cases over rhetorical disagreement;
- pre-specified analyses over post-hoc metric selection;
- reporting null or negative results over protecting a preferred theory.

Open the strongest objection you can make in [Issue #1](https://github.com/hippoley/PAJ-Eval/issues/1).
