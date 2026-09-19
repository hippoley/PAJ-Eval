# PAJ-Eval

### What does AI leave behind in the human?

PAJ-Eval is a **playable evaluation environment for post-assistance judgment**.

Most AI evaluations ask whether the task was completed while the model was present. PAJ-Eval asks a different question:

> After the assistant disappears, can the person still notice what matters, seek the right evidence, revise a bad frame, and act under uncertainty?

The instrument does not present itself as a questionnaire. Participants enter ordinary-looking product and operations environments, make real choices, inspect evidence, hesitate, revise, and experience consequences. The research signal is inferred from that trajectory.

**Current build:** 8 playable journeys · multilingual participant surface · durable event trace · replay/research transport · causal validity contracts.

[Open the Stage](docs/stage.html) · [Participant entry](docs/index.html) · [Research surface](docs/research.html) · [Study protocol](STUDY_PROTOCOL_v0.2.md)

---

## Play first

The current Stage contains eight journeys. The first three establish the design language:

| Journey | What it feels like | What is observed |
| --- | --- | --- |
| **01 · Choice changes the world** | Smart-home shop → offers → urgent travel | what the person carries forward after an apparently ordinary choice |
| **02 · Three systems are failing** | Production incident → fulfillment control tower → home energy | whether investigation behavior transfers across different operational grammars |
| **03 · Three verification desks** | Procurement RFQ → workspace review → service contract | whether the person notices missing provenance and actively asks for evidence |

The participant-facing worlds do **not** expose the latent construct, target score, or a “find the cause” instruction.

```text
ordinary workspace
      ↓
inspect / ignore / compare / act
      ↓
partial consequence
      ↓
revisit / switch / commit
      ↓
novel world with a different surface grammar
```

The object being measured is the trajectory, not a single answer.

---

## Why this exists

AI can make a person faster while it is present and still change what happens afterward.

A useful distinction is:

- **Nominal control** — the human can still approve, reject, interrupt, or redirect the AI.
- **Epistemic control** — the human can independently notice missing evidence, construct a competing frame, recognize that the wrong problem is being solved, and know when rejection is warranted.

PAJ-Eval tests the second claim behaviorally.

It is intentionally designed so that two assistance policies can look equally successful on the assisted task while leaving different downstream investigation behavior.

> The central hypothesis is not that AI necessarily weakens judgment. It is that task-success metrics alone cannot tell us what kind of judgment the interaction leaves behind.

---

## Instrument design

A valid post-assistance world has three properties:

1. **The assistant is absent.**
2. **The next problem is not pre-framed.**
3. **Evidence acquisition is endogenous.** The participant decides what to inspect, what to ignore, when to stop, and when to act.

The observable sequence is:

```text
observation
→ framing
→ hypothesis
→ evidence acquisition
→ revision
→ stopping
→ action
```

The current playable branch pushes this further: different worlds should not feel like the same benchmark template with new labels. Production operations, logistics, energy, sourcing, workspace review, and vendor management use different interface grammars while preserving the research contract underneath.

---

## What is already executable

### Playable participant layer

- 8 interactive journeys
- localized participant packs
- world-specific UI grammars
- provisional actions and partial consequences
- revision / switch / commit behavior
- evidence-request behavior
- non-persisting Stage preview
- participant consent flow

### Research transport

- durable event traces
- replay-oriented research surface
- browser/session tests
- release-gate contracts
- duplicate-safe ingestion path
- separation between participant-facing and researcher-facing information

### Formal measurement work

The repository also contains the earlier formal benchmark work:

- synthetic causal worlds with known latent state
- finite investigation budgets
- expected information value
- Expected Research Utility (ERU)
- oracle / heuristic policy separation
- counterfactual world pairs
- validity and failure-condition documents

Those pieces remain the measurement substrate; the playable layer is the human-facing instrument built on top.

---

## A benchmark that should be easy to kill

PAJ-Eval should not advance merely because the interface looks convincing or the tests pass.

The instrument must survive:

- **counterfactual sensitivity** — similar surface evidence can require different investigations;
- **surface invariance** — cosmetic rerendering should not change the normative world state;
- **heuristic resistance** — fixed shortcuts should remain meaningfully below stronger policies;
- **expert coherence** — useful benchmark evidence should also look scientifically useful to blinded experts;
- **leakage audit** — wording and visual hierarchy must not reveal the intended answer;
- **omitted-action audit** — experts can identify investigations missing from the action space;
- **reward robustness** — modest prior/cost changes should not arbitrarily reverse conclusions;
- **discriminant validity** — the score should not collapse into ML trivia or generic Bayesian numeracy.

See [MEASUREMENT_VALIDITY.md](MEASUREMENT_VALIDITY.md), [SPEC.md](SPEC.md), and [STAGE1A_COUNTERFACTUAL_PAIR.md](STAGE1A_COUNTERFACTUAL_PAIR.md).

---

## Repository map

```text
docs/
  stage.html                 playable-first Stage
  challenge*.html            participant journeys
  research.html              researcher / replay surface
  study.html                 consent + study entry

paj_eval/                    formal benchmark core
tests/                       contracts and regression tests
assets/                      research and visual assets

SPEC.md                      measurement specification
STUDY_PROTOCOL_v0.2.md       causal study design
MEASUREMENT_VALIDITY.md      kill criteria / validity plan
V4_DESIGN_CONTRACT.md        playable instrument contract
DEPLOYMENT_CONFIG.md         deployment and release notes
```

## Run locally

```bash
python -m pip install -e .
pytest -q
```

For the participant UI, serve the repository root or `docs/` with a local static server and open `docs/stage.html`.

---

## What would falsify this?

The most useful contribution is not “this looks interesting.” It is a concrete way the construct can fail.

- Is the instrument measuring judgment, or interface literacy?
- Can a simple visual heuristic reproduce the supposed signal?
- Does the behavior transfer when the entire product grammar changes?
- Are participants seeking evidence because they noticed uncertainty, or because the UI nudged them?
- Can the same assistance information, presented in a different order, change downstream behavior without changing assisted-task success?
- What observation would make the post-assistance interpretation untenable?

Open the strongest objection you can make.

— **Jialun Lin**