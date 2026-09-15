# PAJ-Eval micro-pilot protocol

Status: pre-validation instrument check. This is not a human-effects study and must not be reported as evidence that one AI interaction style preserves judgment better than another.

## Purpose

Before expanding the benchmark or contacting external researchers, try to falsify the current post-assistance judgment instrument with a very small blinded walkthrough.

The immediate question is narrower than treatment effects:

> Can a technically experienced participant encounter an open-ended system handoff, produce an unprompted next-step response before any menu appears, and reveal a distinction between merely recognizing a listed diagnosis and independently opening a useful alternative question?

## Participants

Recruit 3-5 people with real debugging or ML/data-system experience who have not seen PAJ-Eval, its README, world labels, oracle, or hypotheses.

Do not recruit only vector-database specialists. At least one participant should be comfortable with ML systems but unfamiliar with the specific implementation family used by a world.

## Blinding

Participants see only a rendered scenario and the neutral handoff prompt. They must not see:

- world IDs or latent causes;
- oracle values or expected-information calculations;
- the paired counterfactual;
- the phrase `latent question`;
- the research hypothesis;
- action menus before the free response is locked.

Coders of the pre-menu response must not see world ID, later action choice, or treatment information.

## Procedure

1. Randomize one rendering from one world family.
2. Show the scenario with the neutral instruction: `Make as much progress as you can on understanding and improving this system.`
3. Ask only: `What would you do next, and why?`
4. Lock the answer before exposing any action menu.
5. Expose the investigation menu and record the first selected investigation plus rationale.
6. Ask whether an important investigation is missing from the menu.
7. Ask for realism, ambiguity, and any wording that seemed to reveal the intended answer.
8. For participants completing more than one world, separate homologous worlds and counterbalance order. Do not reveal that two worlds share a hidden structure.

## Primary pre-menu observations

Blind-code whether the response:

- opens a concrete alternative question not supplied by the prompt;
- proposes a discriminating next observation or intervention;
- distinguishes source state from a derived/served artifact when relevant;
- commits prematurely to the salient story;
- remains generic (`inspect logs`, `look at metrics`) without identifying what uncertainty the action resolves.

The current binary/specificity coding pipeline is a starting point, not a validated scale.

## Cross-domain check

Use both the retrieval/index-freshness family and the feature-store/materialization family.

The point is not to reward knowledge of either product. The diagnostic pattern is stronger when a participant can independently reopen an analogous source-versus-derived-artifact question across technically different surfaces.

Do not call this transfer until the worlds have survived expert review and the participant has not been trained on the shared pattern.

## Kill criteria for the instrument

Revise or discard a world before external outreach if any of the following occurs:

1. **Obviousness:** most technically experienced participants identify the intended hidden issue immediately from a single giveaway clue.
2. **No counterfactual sensitivity:** participants give essentially the same justified first move in both members of a pair.
3. **Menu creation:** participants rarely open the question pre-menu but reliably select it after seeing the menu.
4. **Domain trivia:** success is tightly tied to prior knowledge of a named tool or implementation rather than the decision structure.
5. **Omitted-action failure:** participants repeatedly propose a plausible higher-value investigation absent from the benchmark action set.
6. **Generic diligence:** broad habits such as `check logs` or `compare prod and offline` score well without resolving a decision-relevant uncertainty.
7. **Surface leakage:** wording, timestamps, status labels, or asymmetric detail reveal the author's intended diagnosis.
8. **Expert incoherence:** experienced reviewers do not agree that the counterfactual evidence should materially change what is worth investigating next.

## What a useful pilot result looks like

A useful result is not a high accuracy number. It is evidence about the instrument itself, for example:

- a clue is too loud and must be weakened;
- the free-response stage captures behavior that the menu stage hides;
- a supposedly homologous world actually requires specialist trivia;
- experts propose an omitted investigation that dominates the authored menu;
- surface changes preserve the decision structure;
- the paired worlds genuinely induce different information priorities.

## What must not be claimed

This micro-pilot cannot establish:

- a causal effect of AI assistance on later judgment;
- that Frame-first or Commit-first is better;
- a validated construct called post-assistance judgment;
- general transfer across domains;
- external validity for scientific research.

Those claims require treatment validation, larger blinded studies, and held-out transfer environments.
