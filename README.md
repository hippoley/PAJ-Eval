# PAJ-Eval

### Same task success. Different humans afterward?

**PAJ-Eval** is an experimental benchmark for **post-assistance judgment**: whether AI interaction policies that produce similar assisted performance can leave people differently able to identify, investigate, revise, and act on a novel problem after the assistant is removed.

> **Core question:** After AI assistance is removed, can a person still determine what is worth investigating when the next problem has not been specified for them?

<p align="center">
  <img src="assets/paj-eval-overview.svg" alt="PAJ-Eval study design" width="100%">
</p>

**Current status:** v0.1 · Stage 0 instrument skeleton · Stage 1A environment falsification next.  
**Research note:** [Same Task Success, Different Humans](https://thirdstructure.wordpress.com/2026/09/15/same-task-success-different-humans/)  
**Canonical repository:** `hippoley/PAJ-Eval`

The earlier artifact in [`hippoley/evals/paj-eval`](https://github.com/hippoley/evals/tree/main/paj-eval) is retained as the original public Stage 0 timestamp.

---

## The missing evaluation object

Most AI evaluations stop when the assisted task ends. They measure what the model can do, or what the human–AI pair can do together.

PAJ-Eval asks a different question: **what can the human independently notice and do afterward, when nobody has framed the next problem for them?**

Three constraints are mandatory:

1. **Assistance is absent** during post-assistance measurement.
2. **The next problem is unframed**: the participant is not told which failure mode, hypothesis family, or reasoning skill to apply.
3. **Information acquisition is endogenous**: the participant chooses what to inspect under a finite budget.

The observable object is a trajectory rather than a single answer:

```text
observation → framing → hypothesis → investigation → revision → stopping → action
```

### Where this sits relative to adjacent work

PAJ-Eval is not trying to re-claim established findings such as “AI can improve current productivity while weakening later mastery.” The intended contribution is narrower.

| Adjacent direction | What it mainly asks | PAJ-Eval adds |
|---|---|---|
| [OpenAI GeneBench-Pro](https://openai.com/index/introducing-genebench-pro/) | Can an AI system exercise research judgment under ambiguity? | What happens to the **human's** independent judgment after repeated AI assistance? |
| [Anthropic TASTE](https://alignment.anthropic.com/2026/taste/) | Can models agree with experts about research quality? | Sequential, behaviorally observed judgment in an **unframed** environment. |
| [Anthropic skill-formation RCT](https://www.anthropic.com/research/AI-assistance-coding-skills) | Does AI assistance change later mastery of a known skill? | Can a person independently determine **what problem is present and what evidence to seek**? |
| [Anthropic disempowerment](https://www.anthropic.com/research/disempowerment-patterns) | Are real-world AI interactions associated with distorted beliefs, values, or actions? | A controlled post-assistance task with known latent ground truth and objective information-seeking opportunities. |

The novelty claim should therefore live or die on one distinction:

> **Known-skill transfer starts after the task has been specified. PAJ-Eval starts one step earlier, where the person must construct the task worth pursuing.**

## Why a synthetic research environment?

“Good judgment” is easy to reduce to a vague expert rubric. PAJ-Eval instead begins with worlds generated from a known latent causal model.

Each investigation has:

- an explicit cost,
- a conditional observation distribution,
- calculable expected information gain (EIG), and
- a downstream effect on terminal decision quality.

This lets the benchmark test whether a research trajectory was informative without assuming that humans should literally behave like Bayesian planners.

The primary decision score is **Research Utility**: terminal decision value minus investigation cost. EIG is a mechanism diagnostic rather than the final objective, because a participant can gather useful information indefinitely and still fail to stop or act.

## A cleaner causal intervention: same information, different order

The original candidate contrast was broad: **frame-supplying** versus **frame-eliciting** assistance. That is useful conceptually, but it risks changing too many things at once: information quantity, number of turns, time, effort, and response content.

The preferred v0.2 intervention is therefore an **information-yoked sequencing design**.

For each assisted training environment, construct one canonical assistance packet containing the same diagnosis-relevant information, hypotheses, evidence interpretation, and recommended next actions.

- **Frame-first condition:** the assistance packet is shown **before** the user records an independent frame or investigation choice.
- **Commit-first condition:** the user must first record an initial frame, competing hypotheses, and next investigation; the **same assistance packet** is then shown.

```text
same task
same base model
same eventual AI information
same assistance packet
        ↓
only the causal order changes
        ↓
AI frame before human commitment
              vs.
human commitment before AI frame
        ↓
assistant removed
        ↓
novel unframed environment
        ↓
post-assistance judgment
```

This does not prove that ordering is the only relevant design variable. It creates a much cleaner first intervention: if post-assistance behavior differs, the result is harder to explain by “one group simply received better or more information.”

**Important identification rule:** assisted-task equivalence is a **design gate**, not a participant-level matching variable. The study should calibrate the two arms to produce equivalent assisted performance ex ante and test that equivalence at the arm level; it should not condition the causal analysis on each participant’s observed post-treatment performance.

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
- commit-first assistance is superior,
- the current reward function captures every defensible scientific strategy, or
- PAJ-Eval is ready for a confirmatory human study.

## Stage 1A: try to kill the instrument before scaling it

The immediate target is deliberately small: build **one adversarial counterfactual pair** before building dozens of worlds.

Two environments should look similar on the surface while having different latent structures, such that the highest-value next investigation changes. If a fixed rule such as

```text
high seed variance → rerun seeds
```

works in both, the pair has failed.

Stage 1A then asks experienced ML researchers to attack the pair while blind to likelihood tables and oracle values.

The instrument advances only if it survives:

- **counterfactual sensitivity** — similar surface, different correct investigation;
- **surface invariance** — same latent world, alternate rendering, comparable action values;
- **heuristic resistance** — cheap fixed strategies stay meaningfully below oracle;
- **expert coherence** — benchmark-preferred evidence is recognizable as useful research evidence;
- **leakage audit** — the latent cause cannot be recovered from superficial wording alone;
- **omitted-action audit** — experts are allowed to identify sensible investigations missing from the action set;
- **reward robustness** — modest cost/reward perturbations do not reverse the whole benchmark.

See [`MEASUREMENT_VALIDITY.md`](MEASUREMENT_VALIDITY.md) and [`STAGE1_BUILD_BRIEF.md`](STAGE1_BUILD_BRIEF.md).

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

The repository has CI enabled; install and test currently pass on the public `main` branch.

## Repository map

```text
PAJ-Eval/
├── README.md
├── SPEC.md
├── MEASUREMENT_VALIDITY.md
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

The highest-value feedback is a concrete way to make the construct fail.

1. **Construct validity:** does this still reduce to Bayesian-game literacy, generic intelligence, or ML trivia?
2. **Identification:** can the information-yoked sequencing design still be explained by differential effort, commitment, or demand effects?
3. **Counterfactual design:** can similar-looking worlds genuinely require different information-seeking actions without becoming artificial?
4. **Scoring:** what scientifically defensible behavior would the current reward model punish?
5. **External validity:** what would have to change before a result in this synthetic lab should generalize to real research workflows?

Open the strongest objection you can make in [Issue #1](https://github.com/hippoley/PAJ-Eval/issues/1).

— **Jialun Lin**, Independent Researcher
