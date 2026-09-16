# PAJ-Eval Probe Families

Probe Player is the participant-facing surface. PAJ-Eval is the measurement program underneath it.

The library is deliberately not a collection of eight mini quizzes. Each family isolates one failure mode in independent judgment formation and must eventually contain causal twins, surface variants, transfer worlds, and an explicit falsification plan.

| Family | Construct under test | What must not become the answer cue |
|---|---|---|
| PF01 Hidden downstream constraints | spontaneous inspection of downstream consequences and option-set changes | words such as compatibility, hidden cost, future options |
| PF02 Competing causal frames | ability to keep and discriminate live alternative explanations | a menu that names the latent causes too directly |
| PF03 Omitted evidence | noticing decision-relevant evidence absent from the foreground | a conspicuous missing-data warning |
| PF04 Anomaly triage | allocating attention by decision value rather than salience | ordering or visual emphasis that reveals the intended anomaly |
| PF05 Experiment selection | choosing tests for discrimination and decision value, not information volume | labeling an experiment as diagnostic or high-EIG |
| PF06 Premature stopping | judging when another investigation can still change the decision | rewarding more clicks or treating diligence as competence |
| PF07 Wrong-problem detection | retaining epistemic control when an assistant supplies a plausible but incomplete frame | making the assistant obviously wrong |
| PF08 Cross-domain spontaneous opening | spontaneous regeneration of useful problem structure after surface/domain change | repeating the intervention vocabulary in transfer |

## Shared participant contract

The participant receives a role, a concrete objective, real affordances, and enough context to act. The participant is not told the latent construct, candidate diagnosis, preferred investigation, or scoring rule. Every visible control must correspond to an ordinary action in the represented world.

There is no required click path. Different behavior trajectories may support the same construct; the same click may support several competing explanations. Primary data are events, timing, state transitions, evidence exposure, revisions, stopping, and commitments.

## Shared evaluation chain

```text
micro-world
  -> raw behavior trajectory
  -> preregistered behavioral features
  -> PAJ construct
  -> validated score (for example SDO / ERU / regret / calibration where appropriate)
  -> causal twin / surface-invariance check
  -> near and far transfer
  -> assistance-policy comparison
```

A trajectory is a sensor reading, not a conclusion. No heuristic score shown by Probe Player should be described as validated PAJ evidence.

## Multilingual contract

Supported player locales in v3: English, Simplified Chinese, Traditional Chinese, Japanese, Korean, Spanish, French, German, Portuguese, and Russian.

Localization is part of measurement validity, not decoration. Confirmatory use requires semantic-equivalence review for task objective, information density, cue strength, action affordances, uncertainty language, and intervention wording. A translated surface must map to the same world state and event ontology. Cross-language invariance should be tested before pooling results.

## Growth gates for every family

A family advances from `seed` to `instrument` only after it has: (1) a latent causal world model; (2) at least one counterfactual twin that changes the useful action without making the surface obviously different; (3) a surface-invariance variant; (4) an omitted-action audit; (5) a no-answer-cue audit; (6) an overreach or negative-transfer world where the target structure should not be applied; (7) a blind expert-coherence check; and (8) a mapping from event traces to a preregistered construct/score.

A family advances from `instrument` to `treatment-ready` only after a naive-participant pilot shows that the world is comprehensible without revealing the research hypothesis and that behavior is sensitive to causal changes rather than cosmetic changes.

## Relation to the original PAJ question

The library exists to operationalize one question: after AI assistance is removed and the next problem is not specified, can a person still independently notice what matters, construct a useful problem representation, seek discriminating evidence, revise, stop, and act?

PF01-PF08 are lenses on that larger process. None of them alone is PAJ-Eval.