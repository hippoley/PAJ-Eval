# PAJ-Eval Human Study Protocol v0.2

**Status:** Design draft for adversarial review — not preregistered, not yet run  
**Purpose:** Make the first human intervention study causally interpretable before recruitment begins.

## 1. Research question

When eventual AI information and assisted-task performance are held approximately constant, does the **order of AI framing relative to a human's own initial problem representation** change subsequent independent judgment after the assistant is removed?

The target is not immediate task success. The target is what the participant independently does next in a novel environment in which the diagnosis or investigation target has not been supplied.

## 2. Closest intervention precedent

The sequencing idea itself is **not a novelty claim**.

Wong & Qiu (2026), *Think First, ChatGPT Later*, randomized 196 university students across human-only, general-AI, and regulated-AI conditions. In the regulated-AI condition, participants first generated their own ideas and then used ChatGPT to develop them; they later outperformed the other groups on an unassisted creative task. This is direct evidence that human-first sequencing can change subsequent independent performance.

PAJ-Eval asks a different downstream question and uses a stricter causal contrast:

- the eventual AI assistance packet is identical across treatment arms;
- the post-assistance environment does not specify the diagnosis or question to solve;
- information acquisition is endogenous and budgeted;
- the first post-assistance response is collected before an investigation menu can cue a hidden alternative;
- the target is research judgment / problem construction rather than independent creativity.

Accordingly, a positive PAJ result should **not** be described as showing for the first time that “thinking first” can improve later unaided performance. The contribution would be evidence about whether an information-yoked framing-order intervention changes later inquiry in an unframed environment.

Reference: Sarah Shi Hui Wong & Sophia Xuefei Qiu (2026), “Think First, ChatGPT Later: Guiding Human–AI Collaboration for Learning Gains in Independent Human Creativity,” *Educational Psychology Review* 38, Article 45. DOI: 10.1007/s10648-026-10118-7.

## 3. Treatment arms

For every assisted training world, precompute one canonical assistance packet. It contains the same substantive hypotheses, evidence interpretation, diagnostic options, and recommended next steps for both arms.

The packet is frozen before data collection, assigned a `packet_id` / content hash, and is never customized from the participant's pre-packet response.

### Frame-first

1. Participant sees the initial research environment.
2. Canonical AI assistance packet is shown.
3. Participant continues the task and may revise or act.

### Self-frame-first

1. Participant sees the same initial research environment.
2. Before AI framing, participant records a **private, non-binding, explicitly revisable** snapshot:
   - initial problem frame,
   - plausible competing explanations,
   - most decision-relevant uncertainty,
   - next investigation they would choose.
3. The exact same canonical AI assistance packet is shown.
4. Participant continues the task and may revise or act.

The participant is explicitly told that the snapshot is provisional, is not scored for consistency, and should be revised when evidence changes.

## 4. What is held fixed

Across arms, hold fixed as far as technically possible:

- base model / packet-generation model,
- initial world state and visible artifacts,
- eventual substantive AI information,
- packet wording and ordering,
- available tools and investigations,
- task budget,
- terminal action set,
- scoring model,
- total assisted task time window.

Log any rescue or deviation from the canonical packet.

## 5. What is intentionally manipulated

The intended treatment difference is whether the participant forms a self-generated problem representation **before** AI provides one.

This may change self-generation, attention, effort, memory, or later revision. These are possible mechanisms, not variables to automatically regress away.

If a two-arm pilot finds an effect, a follow-up should include an **effort-yoked control** to distinguish self-framing from generic extra cognitive effort.

## 6. Population

Initial pilot population: participants with basic ML / data-analysis competence sufficient to interpret logs, metrics, training curves, and common failure modes.

Before randomization, collect:

- short factual ML knowledge screen,
- self-reported years of relevant experience,
- prior AI-assistant usage frequency,
- one baseline no-AI research world.

These are pre-treatment covariates and can improve precision without conditioning on post-treatment behavior.

## 7. Procedure

### Session 1

1. Consent + instructions.
2. 10-minute expertise / knowledge screen.
3. One baseline no-AI world.
4. Random assignment to Frame-first or Self-frame-first.
5. Three assisted training worlds, approximately 15 minutes each.
6. Treatment-fidelity and effort measures collected continuously.

### Delayed session

Target delay: approximately 7 days.

1. No AI assistance.
2. Two held-out, unframed research worlds.
3. At least one world should use a held-out mechanism family or causal composition rather than only a lexical reskin.
4. Participants receive only a sparse work instruction.
5. **Before any investigation menu appears**, collect and lock one free response: `What would you do next, and why?`
6. Only after that response is locked may the structured investigation interface appear.

The pre-menu response is essential: if the action menu is visible first, recognition of a benchmark-supplied alternative can be mistaken for spontaneous problem construction.

## 8. Confirmatory endpoint and mechanism endpoint

The first confirmatory study retains **one primary outcome**:

> **Post-assistance Expected Research Utility (ERU)** across held-out unframed worlds.

ERU evaluates terminal decision quality given the evidence available at the time, minus investigation cost.

A pre-specified **key mechanism endpoint** is collected before the menu:

> **Spontaneous Diagnostic Opening (SDO):** whether the participant independently opens a decision-relevant alternative problem representation before candidate investigations are supplied.

SDO is coded blind to treatment, world identity, later action choice, and outcome. Two independent coders receive only the locked pre-menu text. A minimal rubric records (a) whether an alternative diagnostic question is opened and (b) its specificity. Disagreement is adjudicated before conditions are revealed.

SDO is not promoted to a second confirmatory primary endpoint in v0.2. This avoids multiplicity while allowing the study to test whether any ERU effect plausibly operates through earlier problem construction. If ERU and SDO diverge, report the divergence rather than collapsing them into a composite score.

Derived or secondary outcomes include:

- oracle regret,
- Realized Research Utility,
- expected EIG per cost,
- first discriminating investigation,
- frame revision,
- stopping quality,
- terminal action quality,
- SDO specificity,
- menu-only recognition (critical alternative first appears after the menu).

## 9. Causal estimand

With randomized treatment assignment `P`:

```text
ATE = E[ERU_post | do(P = SelfFrameFirst)]
    - E[ERU_post | do(P = FrameFirst)]
```

The study should permit positive, null, or negative effects.

A null result under a validated instrument is informative and weakens the claim that self-framing order itself changes post-assistance judgment.

## 10. Assisted performance equivalence

Assisted-task equivalence is a **design-validity gate**, not a participant matching rule.

Before confirmatory data collection:

- calibrate the task and packet so both arms achieve practically similar assisted performance;
- preregister an equivalence margin;
- test equivalence at the arm level, for example with TOST.

Do **not** match or condition participants on observed assisted performance after treatment assignment.

## 11. Analysis model

A candidate mixed-effects specification:

```text
ERU_ij = β0
       + β1 Treatment_i
       + β2 BaselineERU_i
       + β3 Expertise_i
       + u_i
       + v_j
       + ε_ij
```

where:

- `u_i` is a participant random intercept,
- `v_j` is a held-out world random intercept.

The first confirmatory analysis should treat `β1` as the primary treatment estimate.

SDO should be analyzed separately with a binary mixed-effects model (or a preregistered simpler alternative if sample size does not support the random-effects structure). It is a mechanism analysis, not a conditioning covariate in the primary ERU model.

Do not automatically control for post-treatment time, effort, turns, SDO, or frame revision in the primary model; those may be mediators. Analyze them separately as mechanisms.

## 12. Treatment-fidelity gates

Before interpreting a treatment effect, verify:

- canonical packet identity / hash matches across arms;
- substantive information exposure is equivalent;
- self-frame snapshot precedes packet exposure in the Self-frame-first arm;
- no hidden personalization of the packet occurred;
- rescue interventions are logged and not severely imbalanced;
- packet exposure and task timing are not systematically broken.

Episodes that violate a preregistered implementation threshold should be treated as fidelity failures, not silently absorbed into the theory test.

## 13. Main threats to interpretation

### Differential effort
Self-frame-first may simply require more thinking. Measure effort from the start; if an effect appears, add an effort-yoked control in the next study.

### Self-generation / desirable-difficulty effects
Wong & Qiu already show that a guided think-first intervention can improve later independent creativity. PAJ must therefore distinguish a general self-generation benefit from the narrower hypothesis about later unframed inquiry. Information-yoking, SDO, and stronger transfer are part of that distinction; an effort-yoked or generation-yoked follow-up may still be necessary.

### Consistency pressure
The pre-packet snapshot could make participants defend their first answer. Reduce this by keeping it private, provisional, non-binding, and explicitly rewarding revision when evidence changes.

### Expertise imbalance
Randomize after baseline measurement and include only pre-treatment expertise covariates.

### Benchmark literacy
Use held-out mechanisms, alternate renderings, anti-shortcut tests, and cross-domain homologs. A participant who knows one vendor-specific failure mode should not automatically score as having transferable post-assistance judgment.

### Demand characteristics
Do not describe the study as testing whether one assistance style makes people “more independent.” Use neutral treatment descriptions and blind participants to the directional hypothesis.

### Menu cueing
Do not expose investigation labels before the locked free response. Otherwise the benchmark itself supplies the alternative question it claims to measure the participant discovering.

### Reward-model brittleness
Freeze scoring before confirmatory collection and report sensitivity to plausible reward / cost perturbations.

## 14. Pilot vs confirmatory study

A small pilot may test feasibility, treatment fidelity, variance, timing, and whether delayed return is practical. It should not be presented as a publication-grade causal result unless powered accordingly.

The confirmatory study requires:

- frozen held-out worlds,
- preregistration,
- simulation-based power analysis,
- one primary endpoint,
- pre-specified equivalence margin for assisted performance,
- fixed exclusion / fidelity rules,
- analysis plan frozen before outcome inspection.

## 15. What would make the treatment design uninteresting?

The treatment hypothesis should weaken if:

- the arms cannot be made equivalent in eventual AI information;
- the self-frame manipulation mostly creates consistency pressure rather than revisable independent framing;
- post-assistance differences vanish under mechanism or compositional transfer;
- the effect is fully reproduced by an effort-yoked or generic self-generation control with no evidence of altered unframed inquiry;
- SDO differences appear only in domain-specific failure modes participants already know;
- results depend on one fragile scoring parameterization.

The purpose of this protocol is not to protect a preferred story. It is to make a null or negative result interpretable.
