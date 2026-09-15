# PAJ-Eval v0.1 — Post-Assistance Judgment Evaluation

**Status:** Experimental specification v0.1  
**Primary domain:** Synthetic ML research environments  
**Primary object:** Human judgment after AI assistance has been removed  
**Author:** Jialun Lin · Independent Researcher

## One-sentence definition

**PAJ-Eval measures whether different AI interaction policies produce different subsequent human judgment when AI is absent, the environment is novel, and the problem itself has not been specified.**

## Mandatory design constraints

A valid post-assistance task must satisfy all three:

1. **Assistance absent.** No assistant is available during the target measurement.
2. **Task unframed.** The participant is not told which hidden problem, causal family, or reasoning procedure to apply.
3. **Information acquisition endogenous.** The participant chooses what evidence to acquire under a finite cost or time budget.

If any of these are removed, the task becomes easier to interpret as ordinary transfer, recall, or skill retention.

## Construct

The behavioral object is:

```text
observation → attention → framing → hypothesis → information acquisition → revision → stopping → action
```

PAJ-Eval does not assume that frame-eliciting assistance is universally beneficial, that direct assistance is harmful, or that any observed treatment difference must be mediated by learning.

## Environment

A synthetic research world is represented as:

```text
W = (Z, D0, A, P(O | Z, a), C(a), R)
```

where:

- `Z` is the latent causal state,
- `D0` is the initially visible evidence,
- `A` is the set of available investigations,
- `P(O | Z, a)` is the observation model,
- `C(a)` is investigation cost,
- `R` is terminal reward as a function of action and latent state.

The first prototype uses ML-diagnosis causes such as preprocessing mismatch, evaluation artifact, optimization instability, and capacity mismatch. Later versions should expand to additional mechanism families and held-out compositions.

## Normative posterior

Given interaction history `H_t`, the benchmark maintains an objective posterior:

```text
b_t(z) = P(Z = z | H_t)
```

This posterior is a property of the benchmark world and observed evidence. It is **not** intended as a psychological model of the participant's subjective belief.

Self-reported hypotheses and confidence, when collected, are secondary behavioral measures.

## Expected information gain

For an investigation `a`:

```text
EIG(a | H_t) = H[b_t] - E_o H[b_{t+1}]
```

A cost-normalized mechanism diagnostic is:

```text
IE(a | H_t) = EIG(a | H_t) / C(a)
```

Cumulative Information Acquisition Efficiency can be reported as:

```text
IAE = Σ_t EIG(a_t | H_t) / Σ_t C(a_t)
```

Expected EIG at choice time is preferred over realized information gain for action-quality analysis because it does not reward stochastic luck.

## Primary endpoint: Research Utility

EIG is not the primary endpoint. A participant may continue gathering information without ever making a useful decision.

Let `u_T` be the terminal action after history `H_T`. Define:

```text
RU = Σ_z b_T(z) R(u_T, z) - λ Σ_t C(a_t)
```

The benchmark reports both raw Research Utility and regret relative to the finite-budget oracle.

## Oracle reference

For the known synthetic world:

```text
π* = argmax_π E[RU | π]
```

The oracle is a benchmark-validation instrument, not a behavioral prescription for humans. Its role is to test whether the environment rewards informative inquiry, appropriate stopping, and correct action rather than arbitrary benchmark conventions.

## Candidate treatments

### Frame-supplying assistance

May proactively provide:

- problem representation,
- leading hypotheses,
- experiment ranking,
- interpretation,
- recommended next action.

### Frame-eliciting assistance

Has access to the same underlying information and technical capability, but first elicits:

- competing explanations,
- uncertainty,
- falsification conditions,
- evidence priorities,
- comparison among candidate investigations.

A rescue ladder may progressively increase support when the user is stuck; rescue level must be logged.

## Identification target

The intervention is interpretable only if assisted performance is approximately matched:

```text
P_assisted^Supply ≈ P_assisted^Elicit
```

This should be tested with an equivalence procedure, not inferred from a nonsignificant difference.

Then, after assistance is removed:

```text
H0: J_post^Supply = J_post^Elicit
H1: J_post^Supply ≠ J_post^Elicit
```

The benchmark should permit either direction.

## Primary and secondary measures

**Primary**

- post-assistance Research Utility,
- oracle regret.

**Mechanism / secondary**

- expected EIG per cost,
- problem discovery,
- frame revision,
- hypothesis diversity,
- calibration,
- false-positive pursuit,
- stopping quality,
- terminal action quality.

## Treatment-fidelity measures

At minimum:

- frame-before-user rate,
- user-generated hypotheses before first supplied frame,
- direct recommendation rate,
- assistant information volume,
- rescue rate,
- interaction time and number of turns,
- blinded audit of policy separation.

## Stage 0 success criterion

Stage 0 succeeds if the environment is executable, metrics are non-degenerate, weak policies are meaningfully separated, and costly activity is not automatically rewarded.

Stage 0 **does not** require evidence that one human-AI interaction policy outperforms another.

## Core falsifiable claim

> **Current assisted performance may be insufficient to identify the long-run human consequence of an AI interaction policy.**
