# PAJ-Eval v0.2 — Post-Assistance Judgment Evaluation

**Status:** Experimental specification v0.2  
**Primary domain:** Synthetic ML research environments  
**Primary object:** Human judgment after AI assistance has been removed  
**Author:** Jialun Lin · Independent Researcher

## One-sentence definition

**PAJ-Eval measures whether AI interaction policy causally changes subsequent human judgment when AI is absent, the environment is novel, the problem itself has not been specified, and the human must choose what evidence to acquire.**

## Mandatory design constraints

A valid post-assistance task must satisfy all three:

1. **Assistance absent.** No assistant is available during the target measurement.
2. **Task unframed.** The participant is not told which hidden problem, causal family, or reasoning procedure to apply.
3. **Information acquisition endogenous.** The participant chooses what evidence to acquire under a finite cost or time budget.

If any are removed, the task becomes easier to interpret as ordinary transfer, recall, or known-skill retention.

## Construct

The behavioral object is:

```text
observation → attention → framing → hypothesis → information acquisition → revision → stopping → action
```

PAJ-Eval is not intended to measure every aspect of intelligence, expertise, creativity, or autonomy. Its narrow target is the process by which a person constructs an actionable problem representation and chooses evidence under uncertainty after AI support has been removed.

## Environment

A synthetic research world is represented as:

```text
W = (Z, D0, A, P(O | Z, a), C(a), R)
```

where:

- `Z` is the latent causal state,
- `D0` is initially visible evidence,
- `A` is the set of available investigations,
- `P(O | Z, a)` is the observation model,
- `C(a)` is investigation cost,
- `R(u, Z)` is the value of terminal action `u` under latent state `Z`.

The initial prototype uses ML-diagnosis causes such as preprocessing mismatch, evaluation artifact, optimization instability, and capacity mismatch. Later versions should include conditional label corruption, leakage/spurious shortcuts, and held-out causal compositions.

## Normative posterior

Given interaction history `H_t`, the benchmark maintains an objective posterior:

```text
b_t(z) = P(Z = z | H_t)
```

This posterior is a property of the benchmark world and observed evidence. It is **not** a psychological model of the participant's subjective belief.

Self-reported hypotheses and confidence are secondary behavioral measures and should never substitute for observed investigation choices.

## Information value

For investigation `a`:

```text
EIG(a | H_t) = H[b_t] - E_o H[b_{t+1}]
```

A cost-normalized mechanism diagnostic is:

```text
IE(a | H_t) = EIG(a | H_t) / C(a)
```

Cumulative Information Acquisition Efficiency may be reported as:

```text
IAE = Σ_t EIG(a_t | H_t) / Σ_t C(a_t)
```

Expected EIG at choice time is preferred over realized information gain for action-quality analysis because it does not reward stochastic luck.

## Decision utility: separate normative quality from outcome luck

The earlier specification used one Research Utility expression for both decision quality and realized outcome. v0.2 separates them.

### Expected Research Utility (primary decision-quality score)

Let `u_T` be the terminal action after history `H_T`:

```text
ERU = Σ_z b_T(z) R(u_T, z) - λ Σ_t C(a_t)
```

ERU asks whether the terminal decision was justified by the evidence available at the time, net of investigation cost. It avoids rewarding or punishing participants merely because a stochastic world realization was lucky.

### Realized Research Utility (secondary ecological outcome)

For the actual latent state `Z*`:

```text
RRU = R(u_T, Z*) - λ Σ_t C(a_t)
```

RRU records what actually happened in the generated world. It is useful as an ecological secondary outcome, but it is noisier as a measure of decision quality.

### Oracle regret

For known synthetic worlds, let `V*(H_0)` be the finite-budget optimal expected utility. Then:

```text
OracleRegret = V*(H_0) - ERU_participant
```

A normalized score may be reported only after environment validation:

```text
NormalizedERU = (ERU_participant - E[ERU_random]) /
                (V*(H_0) - E[ERU_random])
```

This normalization is descriptive, not a claim that the oracle defines human rationality.

## Oracle reference

```text
π* = argmax_π E[ERU | π]
```

The oracle is a benchmark-validation instrument, not a behavioral prescription. Its role is to verify that the environment rewards informative inquiry, appropriate stopping, and evidence-supported action rather than arbitrary benchmark conventions.

## Preferred treatment design: information-yoked sequencing

A broad contrast between “direct” and “eliciting” assistants changes too many variables at once. v0.2 therefore specifies a cleaner first intervention.

For each assisted training environment, construct a **canonical assistance packet** containing the same substantive AI information for both arms: relevant hypotheses, interpretation of evidence, diagnostic options, and recommended next steps.

### Frame-first arm

The canonical assistance packet is shown **before** the participant records an independent problem frame, competing hypotheses, or next investigation.

### Commit-first arm

Before seeing the canonical assistance packet, the participant records:

- an initial problem frame,
- at least two plausible explanations where applicable,
- the uncertainty they consider most important,
- the next investigation they would choose.

The **same assistance packet** is then shown.

Subsequent technical assistance should be kept as similar as practicable across arms.

This intervention primarily changes **causal order**, not eventual information access.

## Identification target

Let `P ∈ {FrameFirst, CommitFirst}` denote randomized treatment assignment.

The primary causal estimand is:

```text
ATE_J = E[J_post | do(P = CommitFirst)]
      - E[J_post | do(P = FrameFirst)]
```

where `J_post` is post-assistance judgment measured in held-out unframed worlds.

### Assisted performance is a design gate, not a conditioning variable

The two arms should be calibrated **before the confirmatory study** to produce practically equivalent assisted-task performance and comparable eventual information exposure.

Arm-level assisted equivalence should be tested with a pre-specified equivalence margin.

Do **not** estimate the treatment effect by conditioning or matching on each participant's observed assisted performance, because assisted performance is post-treatment and conditioning on it can distort the causal comparison.

### What is allowed to differ?

The total effect of the sequencing policy may legitimately include changes in:

- cognitive effort,
- self-generation,
- commitment,
- attention allocation.

These may be mechanisms rather than nuisance variables. They should be measured, not automatically regressed away.

A secondary mechanism analysis may examine whether treatment effects co-vary with pre-assistance commitment quality, effort, or frame revision, but such analyses should be labeled exploratory unless separately powered and preregistered.

## Post-assistance measurement

A valid held-out test environment must differ from assisted training on more than superficial nouns.

Preferred transfer levels:

1. **Surface transfer:** same latent mechanism, different rendering.
2. **Mechanism transfer:** held-out latent mechanism family.
3. **Compositional transfer:** novel combination of previously seen causal components.
4. **Domain transfer:** different technical surface domain with preserved decision structure.

The main confirmatory endpoint should be chosen before data collection; stronger claims require stronger transfer levels.

## Primary and secondary measures

**Primary**

- post-assistance Expected Research Utility (ERU),
- oracle regret.

**Secondary / mechanism**

- Realized Research Utility,
- expected EIG per cost,
- time to first discriminating investigation,
- frame revision after disconfirming evidence,
- hypothesis diversity,
- calibration,
- false-positive pursuit,
- stopping quality,
- terminal action quality,
- proportion of budget spent before first meaningful frame revision.

## Treatment-fidelity measures

At minimum:

- whether independent commitment occurred before AI frame exposure,
- frame-before-user rate,
- substantive information overlap between arms,
- assistant token/information volume,
- direct recommendation rate,
- rescue rate,
- interaction time and number of turns,
- participant effort proxies,
- blinded human audit of treatment separation.

The confirmatory study should specify a fidelity threshold below which an episode or study arm is considered implementation failure rather than evidence about the theory.

## Construct-validity battery

Before any confirmatory intervention study, the environment must pass tests for:

- counterfactual sensitivity,
- surface invariance,
- heuristic resistance,
- expert coherence,
- latent-cause leakage,
- omitted-action coverage,
- reward robustness,
- discrimination from factual ML knowledge and generic Bayesian numeracy.

See [`MEASUREMENT_VALIDITY.md`](MEASUREMENT_VALIDITY.md).

## Stage 0 success criterion

Stage 0 succeeds if the environment is executable, metrics are non-degenerate, weak policies are meaningfully separated, costly activity is not automatically rewarded, and public CI reproduces installation and tests.

Stage 0 **does not** require evidence that one human-AI interaction policy outperforms another.

## Core falsifiable claim

> **Two AI interaction policies can be equivalent on assisted-task performance yet produce measurably different subsequent human judgment in a novel unframed environment.**

The null result is scientifically meaningful: if information-yoked sequencing does not change post-assistance judgment under a validated instrument, then the stronger version of this hypothesis should weaken.
