# PAJ-Eval

### Same task success. Different humans afterward?

**PAJ-Eval** is an experimental benchmark for **post-assistance judgment**: whether AI interaction policies that produce similar assisted performance can leave people differently able to identify, investigate, revise, and act on a novel problem after the assistant is removed.

> **Core question:** After AI assistance is removed, can a person still determine what is worth investigating when the next problem has not been specified for them?

<p align="center">
  <img src="assets/paj-eval-overview.svg" alt="PAJ-Eval study design" width="100%">
</p>

**Current status:** v0.1 · Stage 0 instrument skeleton · advancing to environment validity.  
**Research note:** [Same Task Success, Different Humans](https://thirdstructure.wordpress.com/2026/09/15/same-task-success-different-humans/)

This repository is the canonical home of PAJ-Eval. The earlier public artifact in [`hippoley/evals/paj-eval`](https://github.com/hippoley/evals/tree/main/paj-eval) is retained as the original Stage 0 public timestamp.

---

## The missing evaluation object

Most AI evaluations stop when the assisted task ends. They measure what the model can do, or what the human–AI pair can do together.

PAJ-Eval asks a different question: **what can the human independently notice and do afterward?**

The construct is intentionally narrower than general AI dependence or skill retention. It targets judgment *before the next task has been framed for the user*.

Three constraints are mandatory:

1. **Assistance is absent** during post-assistance measurement.
2. **The next problem is unframed**: the participant is not told which failure mode, hypothesis family, or reasoning skill to apply.
3. **Information acquisition is endogenous**: the participant chooses what to inspect under a finite budget.

The observable object is therefore a trajectory, not a single answer:

```text
observation → framing → hypothesis → investigation → revision → stopping → action
```

## Why a synthetic research environment?

“Good judgment” is easy to reduce to a vague expert rubric. PAJ-Eval instead begins with worlds generated from a known latent causal model.

Each investigation has:

- an explicit cost,
- a conditional observation distribution,
- calculable expected information gain (EIG), and
- a downstream effect on terminal decision quality.

This makes it possible to ask whether a research trajectory was informative without assuming that humans should behave exactly like a Bayesian planner.

The primary score is **Research Utility**: terminal decision value minus investigation cost. EIG is retained as a mechanism diagnostic rather than the final objective, because a participant can gather useful information indefinitely and still fail to stop or act.

## The causal experiment PAJ-Eval is meant to enable

The intended experiment is **not AI vs. no AI**.

It compares interaction policies using the same underlying model capability, for example:

- **Frame-supplying assistance** — may proactively provide the problem representation, leading hypotheses, experiment ranking, interpretation, and next action.
- **Frame-eliciting assistance** — has access to the same factual and technical capability, but first elicits competing explanations, uncertainty, falsification conditions, and evidence priorities before supplying the higher-level frame.

The design target is:

```text
matched assisted performance
        ↓
assistant removed
        ↓
novel environment + problem unspecified
        ↓
measure what the human does next
```

The experiment should **not** assume in advance that either policy preserves judgment better.

## Stage 0: executable sanity check

The current toy world contains four hidden causes, seven investigations, a finite budget, stochastic observations, posterior updates, Research Utility, and an exact finite-budget oracle planner.

A deterministic sanity check over 300 simulated episodes per policy gives:

| Policy | Mean expected Research Utility | Mean cost | Mean EIG | Mean steps |
|---|---:|---:|---:|---:|
| Oracle | **4.417** | 3.593 | 0.759 | 1.710 |
| Greedy EIG/cost | 3.442 | 5.310 | **0.925** | 2.537 |
| Random | 0.295 | 5.027 | 0.448 | 2.063 |
| Expensive-bias | -4.567 | 8.000 | 0.195 | 2.000 |

![Stage 0 policy separation](assets/stage0-policy-separation.svg)

The useful signal is not simply that the oracle wins. **Greedy information gathering accumulates more raw EIG than the oracle while achieving lower Research Utility.** The environment therefore distinguishes information collection from the broader judgment problem of stopping and acting. Expensive activity is not automatically rewarded.

Stage 0 establishes only that the construct can be represented as a non-degenerate executable decision environment.

It does **not** establish that:

- AI assistance changes human judgment,
- this toy world already measures real research judgment,
- frame-eliciting assistance is superior, or
- PAJ-Eval is ready for a confirmatory human study.

## The next falsification

The immediate target is not simply “more worlds.” It is **counterfactual world pairs** with similar visible evidence but different latent causes, such that the highest-value next investigation changes.

If a participant can learn a fixed rule like:

```text
high seed variance → rerun seeds
```

then the benchmark is measuring benchmark-pattern recognition rather than judgment.

The next environment must force the harder question:

> **Given everything observed so far, which next action would most change what I should believe or do?**

See [`STAGE1_BUILD_BRIEF.md`](STAGE1_BUILD_BRIEF.md) for the environment-validity program.

## Alignment implication under test

PAJ-Eval is motivated by a distinction between two forms of human control:

- **Nominal control:** the human retains the formal right to approve, reject, interrupt, or redirect the system.
- **Epistemic control:** the human can independently notice missing evidence, construct a competing problem representation, recognize when the system is solving the wrong problem, and know when rejection is warranted.

> A human can retain the right to reject an AI while losing some of the independent judgment required to know when rejection is warranted.

This is a hypothesis to test, **not a result already established**.

## Run the prototype

```bash
python -m pip install -e .
python demo.py
pytest -q
```

Expected test result:

```text
4 passed
```

The simulation outputs are written to `outputs/`.

## Repository map

```text
PAJ-Eval/
├── README.md
├── SPEC.md
├── VALIDATION.md
├── REPRODUCIBILITY.md
├── STAGE_GATES.md
├── STAGE1_BUILD_BRIEF.md
├── CITATION.cff
├── CONTRIBUTING.md
├── LICENSE
├── demo.py
├── pyproject.toml
├── paj_eval/
├── tests/
├── outputs/
└── assets/
```

## What would be most useful to challenge?

I am especially interested in adversarial feedback on four questions:

1. **Construct validity:** does this measure research judgment, or merely competence at a Bayesian game?
2. **Counterfactual design:** can superficially similar worlds genuinely require different information-seeking actions without becoming artificial?
3. **Treatment validity:** can assistance policies be separated without confounding information quantity, model quality, effort, or time?
4. **Human-study interpretation:** what result would actually distinguish post-assistance judgment from ordinary learning transfer or expertise effects?

If you work on research-judgment evals, human–AI interaction, scalable oversight, model behavior, or long-horizon user capability, please open an issue with the strongest objection you can make.

— **Jialun Lin**, Independent Researcher
