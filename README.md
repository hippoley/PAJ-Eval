# PAJ-Eval — A Playable Benchmark for Human Judgment After AI Assistance

### Same task success. Different humans afterward?

**PAJ-Eval** is an open, playable benchmark for a question most AI evaluations still stop before asking:

> **When the assistant disappears, what kind of judgment is left in the human?**

AI systems are increasingly good at completing tasks, proposing next steps, and even making research-level judgment calls. But task success while assistance is present does not tell us whether a person can still **notice what matters, frame a novel problem, seek discriminating evidence, revise a bad hypothesis, and know when to act** once the AI is gone.

PAJ-Eval turns that question into an interactive behavioral instrument.

Instead of asking participants to rate an assistant, it places them inside ordinary-looking product, operations, procurement, travel, support, experiment, and facilities software. They inspect what they want, ignore what they want, make provisional decisions, experience consequences, revisit evidence, switch course, and eventually commit.

The benchmark records the **trajectory of judgment** rather than only the final answer.

<p align="center">
  <img src="assets/paj-eval-overview.svg" alt="PAJ-Eval human-AI interaction and post-assistance judgment benchmark" width="100%">
</p>

**Current build:** 8 playable journeys · multilingual participant surfaces · durable event traces · replay tooling · counterfactual validity tests · synthetic causal worlds with known ground truth.

[Play the Stage](docs/stage.html) · [Participant entry](docs/index.html) · [Research replay](docs/research.html) · [Study protocol](STUDY_PROTOCOL_v0.2.md) · [Measurement validity](MEASUREMENT_VALIDITY.md)

---

## Why this problem matters now

The frontier is moving from “Can AI answer?” toward “Can AI make good judgment calls under ambiguity?”

OpenAI's [GeneBench-Pro](https://openai.com/index/introducing-genebench-pro/) evaluates research judgment in messy computational-biology tasks. Anthropic's [TASTE](https://alignment.anthropic.com/2026/taste/) studies whether models can judge AI-safety research proposals. Work on [agentic AI evaluation](https://link.springer.com/article/10.1007/s10462-026-11571-0) increasingly treats multi-step trajectories and judgment as first-class evaluation objects.

At the same time, a different literature is asking what AI assistance does to the **human**:

- [HumanAgencyBench](https://arxiv.org/abs/2509.08494) evaluates whether assistants support human agency.
- Anthropic's [disempowerment research](https://www.anthropic.com/research/disempowerment-patterns) studies how AI interactions can shape beliefs, values, and actions.
- Randomized studies of [coding skill formation](https://www.anthropic.com/research/AI-assistance-coding-skills) and [logic-puzzle learning](https://arxiv.org/abs/2608.23543) examine performance after assistance is removed.
- A 2026 field experiment in [patent drafting](https://www.nber.org/papers/w35720) studies whether AI-enhanced work translates into later unassisted professional judgment.
- Recent work on [meaningful human oversight](https://link.springer.com/article/10.1007/s43681-026-01147-7) and [epistemic control](https://link.springer.com/article/10.1007/s00146-026-03281-6) argues that retaining a formal approve/reject button is not the same as retaining the judgment required to use it well.

PAJ-Eval sits at the intersection of these lines of work.

### The missing evaluation layer

Most existing approaches measure one of three things:

| Evaluation target | Typical question |
| --- | --- |
| **Model capability** | Can the AI reason, judge, plan, or use tools? |
| **Assisted performance** | Does the human–AI pair complete the current task better? |
| **Skill retention** | Can the person later perform a known task without help? |

PAJ-Eval adds a fourth:

> **Post-assistance judgment:** when the next problem is novel and not pre-framed, can the person still decide what deserves attention, what evidence would discriminate between explanations, when a frame is wrong, and when enough is enough?

That distinction matters because a person can retain **nominal control** over an AI system while losing some of the **epistemic control** needed to know when intervention is warranted.

This is a hypothesis to test, not a conclusion already established.

---

## Play first, then inspect the construct

The participant-facing instrument is deliberately not presented as a psychology questionnaire or an “AI safety task.”

Each journey uses a different product grammar so that successful behavior cannot reduce to learning one benchmark interface.

| Journey | Surface world | What changes |
| --- | --- | --- |
| **01 · Choice changes the world** | smart-home shop → offers → urgent travel | downstream consequences of an apparently ordinary choice |
| **02 · Systems are failing** | production console → fulfillment control tower → building energy | transfer of investigation behavior across operational domains |
| **03 · Verification desks** | procurement RFQ → workspace review → service contract | missing provenance, evidence requests, and commitment |
| **04 · Operational incidents** | checkout incident → delivery disruption → travel disruption | triage order and distractor abandonment |
| **05 · Costly experiments** | launch experiment → quality lab → field test | information value under explicit budget and opportunity cost |
| **06 · Recovery windows** | service recovery → dispatch → home automation | timing, waiting, rollback, and shrinking option sets |
| **07 · Objective drift** | product plan → support automation → shuttle scheduler | whether polished solutions trigger checks against the original objective |
| **08 · Open workspaces** | operations ledger → event control room → facilities CMMS | what people open first when nobody tells them what problem exists |

The participant sees ordinary work.

The instrument records behavior such as:

```text
what was opened first
→ what was ignored
→ which evidence was inspected deeply
→ provisional action
→ consequence
→ revisit / revision / switch
→ stopping
→ final commitment
```

No live “agency score” or latent construct label is shown to the participant.

---

## What PAJ-Eval is trying to measure

The target is not generic intelligence, obedience, confidence, or interface literacy.

A post-assistance task is valid only when:

1. **Assistance is absent.**
2. **The next problem is not already framed.**
3. **Evidence acquisition is endogenous.**
4. **More activity is not automatically better.**
5. **A plausible but wrong path is available.**
6. **The environment can reveal whether revision was justified.**

The central behavioral object is:

```text
observation
→ problem framing
→ competing hypotheses
→ evidence acquisition
→ belief revision
→ stopping
→ action
```

This makes PAJ-Eval closer to a **behavioral human-AI interaction benchmark** than to a conventional question-answer dataset.

---

## Same information, different interaction policy

A broad comparison like “direct assistant vs. Socratic assistant” changes many variables at once.

The confirmatory design instead uses **information-yoked assistance**.

Both conditions ultimately receive the same substantive assistance packet. What changes is the order in which the human forms their own representation relative to the AI frame.

```text
same task
same eventual AI information
same assistance packet
        ↓
AI frame before self-frame
              vs.
self-frame before AI frame
        ↓
assistant removed
        ↓
novel unframed environment
        ↓
post-assistance judgment trajectory
```

This isolates a narrower causal question:

> Does the sequencing of AI framing change what people independently notice and investigate later, even when assisted-task information is held constant?

See [STUDY_PROTOCOL_v0.2.md](STUDY_PROTOCOL_v0.2.md).

---

## The benchmark has ground truth underneath the play

The playable surfaces sit on top of synthetic worlds whose latent causal structure is known.

Investigations can have:

- explicit costs,
- observation distributions conditioned on hidden causes,
- expected information gain,
- downstream decision value,
- reversible or irreversible consequences,
- finite budgets and shrinking action windows.

The formal layer can therefore distinguish:

**“I collected more information”**

from

**“I collected the information that was worth collecting before acting.”**

The confirmatory utility measure is **Expected Research Utility (ERU)**: evidence-justified terminal decision value minus investigation cost. Realized outcome is tracked separately so that good judgment is not confused with good luck.

The repository includes exact planners and heuristic baselines for sanity checking these worlds.

---

## A benchmark that should be easy to kill

PAJ-Eval should not survive because the story is persuasive.

It should survive because alternative explanations fail.

Before treatment claims are credible, the instrument must pass:

- **counterfactual sensitivity** — similar-looking worlds can require different investigations;
- **surface invariance** — visual rerendering should not change the normative state;
- **heuristic resistance** — fixed shortcuts remain meaningfully below stronger policies;
- **expert coherence** — benchmark-preferred evidence is recognizable as useful by domain experts;
- **leakage audit** — wording, layout, and salience do not expose the intended path;
- **omitted-action audit** — experts can propose investigations missing from the action space;
- **reward robustness** — modest prior/cost changes do not arbitrarily reverse the benchmark;
- **discriminant validity** — performance does not collapse into domain trivia, numeracy, or UI familiarity;
- **transfer validity** — a learned interface routine should not explain cross-domain effects.

See [MEASUREMENT_VALIDITY.md](MEASUREMENT_VALIDITY.md), [SPEC.md](SPEC.md), and [STAGE1A_COUNTERFACTUAL_PAIR.md](STAGE1A_COUNTERFACTUAL_PAIR.md).

---

## Who this is useful for

PAJ-Eval is relevant if you work on:

- **human-AI interaction** and cognitive offloading,
- **AI evaluation** beyond task accuracy,
- **human agency** and AI-assisted decision-making,
- **AI safety** and meaningful human oversight,
- **agentic systems** where humans supervise increasingly capable agents,
- **skill formation** and expertise under AI assistance,
- **behavioral benchmarks** with trajectory-level measurement,
- interfaces that aim to preserve human judgment rather than only maximize immediate productivity.

The project is intentionally open to competing interpretations. If a simpler construct explains the behavior better than “post-assistance judgment,” that is useful evidence.

---

## Repository map

```text
docs/
  stage.html                 playable Stage
  challenge*.html            eight participant journeys
  research.html              replay / researcher surface
  study.html                 consent + formal study entry

paj_eval/                    causal world + formal benchmark core
tests/                       contracts, browser and regression tests
assets/                      diagrams and benchmark figures

SPEC.md                      measurement specification
STUDY_PROTOCOL_v0.2.md       causal study design
MEASUREMENT_VALIDITY.md      validity and falsification plan
V4_DESIGN_CONTRACT.md        playable instrument contract
DEPLOYMENT_CONFIG.md         deployment / transport notes
```

## Run locally

```bash
python -m pip install -e .
pytest -q
```

Serve the repository root (or `docs/`) with a local static server, then open:

```text
docs/stage.html
```

---

## What would falsify the idea?

The highest-value contribution is a concrete failure mode.

- Is this measuring judgment, or merely conscientiousness?
- Is evidence seeking driven by UI salience rather than uncertainty?
- Can a simple “always inspect X first” policy reproduce the effect?
- Does the signal survive when the entire product grammar changes?
- Does post-assistance behavior predict anything outside the synthetic worlds?
- Can the same information ordering effect be explained by extra effort or consistency pressure?
- What observation would make “epistemic control” the wrong interpretation?

If you can break the construct, open the strongest objection you can make.

— **Jialun Lin**
