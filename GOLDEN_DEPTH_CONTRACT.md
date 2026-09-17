# Golden Depth Contract

PAJ-Eval is not a collection of quiz cards. The participant should feel that they are using an ordinary application, making an ordinary decision, and discovering ordinary consequences. Research constructs stay downstream.

The preserved Inception shopping → offer → travel journey is the interaction reference. Every probe family must eventually reach at least this depth before it is considered complete.

## 1. The irreducible journey shape

Every full probe family is a journey, not a single screen:

1. **Seed world** — a concrete task with enough ordinary objects to explore freely.
2. **Consequence** — an action changes the world or the remaining option set. The interface shows the consequence; it does not explain the construct.
3. **Minimal intervention** — at most one short structural sentence. It may point at a relation, never at a correct answer.
4. **Near transfer** — a new domain with a related structural problem and different surface vocabulary.
5. **Far transfer** — a substantially different domain with no repeated diagnostic vocabulary.
6. **Raw trajectory** — append-only actions, timing, object openings, nested detail openings, state changes, and final action.
7. **Research inference** — versioned and downstream. Never used to steer the participant while the journey is live.

The core scientific object is not whether the participant picked the answer we expected. It is whether a useful investigative structure appears, survives consequence, and reappears in new worlds after assistance is removed.

## 2. Minimum interaction depth per world

A world fails this contract if it is only a decorated multiple-choice question.

Each seed / near-transfer / far-transfer world must expose:

- at least **5 ordinary top-level objects** when the domain naturally supports them;
- at least **2 nested objects or drill-down paths**;
- at least **1 meaningful action** that changes world state;
- at least **1 optional omission** that remains measurable if the participant never opens it;
- a terminal action that is possible without following a required research path;
- no correctness feedback during play;
- no construct labels, latent-variable names, posterior scores, or research vocabulary on participant surfaces.

Across the journey there must be:

- at least **1 consequence that changes the remaining option space**;
- at least **1 post-consequence action**;
- at least **1 transfer world with a provisional action, an ordinary stateful consequence, and a chance to revise before terminal commitment**;
- the far-transfer world must not collapse into a static answer card: it must preserve optional evidence, nested evidence, and a reversible pre-commit state;
- a near transfer and a far transfer;
- enough ordinary information that a diligent but construct-irrelevant browsing strategy is possible. This is necessary to distinguish targeted transfer from generic conscientiousness.

A seed consequence alone is not sufficient evidence of transfer. The instrument must be able to observe whether the participant spontaneously reconstructs the relevant investigative structure when the vocabulary, objects, and domain have changed.

## 3. Golden interaction tests

A new design is a regression if any of these become false:

- The participant can act immediately without being forced through explanatory text.
- The participant can open real objects rather than buttons named after research variables.
- Objects can contain other objects.
- Consequences appear as changes in the world, not as researcher narration.
- A useful path can be omitted.
- A participant can change course after a consequence.
- A transfer-world decision can remain provisional long enough for ordinary consequences to become visible.
- The next domain does not reuse the previous domain's vocabulary as a cue.
- Raw behavior remains separable from research interpretation.

## 4. Localization is world design, not string translation

The invariant is the **experimental grammar**, not the literal nouns, prices, cities, or UI copy.

Every supported locale must map to an explicit market pack. A market pack can change:

- currency and believable price relationships;
- product naming and retail conventions;
- delivery and return language;
- local work / contract / commute conventions;
- local transport and airport / station assumptions;
- city names and geographic scale;
- date, number, address, and time conventions;
- idiom, register, button verbs, and customer-review tone.

A localized world is invalid if it is merely the same Chinese or US world translated word-for-word.

Current explicit market mapping:

| Locale | Market | Currency |
|---|---|---|
| en | US | USD |
| zh-CN | CN | CNY |
| zh-TW | TW | TWD |
| ja | JP | JPY |
| ko | KR | KRW |
| es | ES | EUR |
| fr | FR | EUR |
| de | DE | EUR |
| pt | BR | BRL |
| ru | RU | RUB |

Portuguese is explicitly Brazilian Portuguese in the first full market pack. A future Portugal pack must be a separate market variant rather than a silent substitution.

## 5. Eight experimental grammars

The eight families are research-side identifiers only. Participant-facing products use ordinary world names.

| Family | Seed world | Consequence | Near transfer | Far transfer |
|---|---|---|---|---|
| PF01 | consumer purchase | cheap choice creates downstream dependency / total-cost change | job offer | time-constrained travel |
| PF02 | production incident | first plausible cause survives until discriminating evidence is opened | operations / fulfillment anomaly | unfamiliar household or service anomaly |
| PF03 | procurement comparison | leading option depends on missing provenance | rental / contract comparison | service-provider choice |
| PF04 | product anomaly triage | several metrics move, only some share the failure path | logistics disruption | travel disruption |
| PF05 | constrained experiment choice | evidence consumes real budget / time | process optimization | unfamiliar field test |
| PF06 | recovery monitor | early success can reverse after delay while rollback window shrinks | shipment recovery | automation recovery |
| PF07 | polished AI plan | plan optimizes the stated metric while stakeholder objective diverges | support automation | scheduling / policy problem |
| PF08 | sparse unfamiliar workspace | relations emerge only through self-directed object opening | new planning domain | a second unfamiliar operational domain |

These are grammars, not fixed stories. Each locale can use different stories if cue strength and action affordances remain comparable.

## 6. Measurement invariance requirements

For cross-language / cross-market use, validate equivalence on:

- number of top-level affordances;
- number and depth of nested evidence paths;
- salience of the target evidence relative to distractors;
- cost of inspection in clicks, time, and reading load;
- severity and reversibility of the consequence;
- strength of the minimal intervention;
- difficulty of near and far transfer;
- terminal-action attractiveness before and after evidence;
- omission opportunity;
- overall task duration distribution.

Literal equality is not the goal. Behavioral comparability is.

## 7. Build order

1. Perfect one complete golden journey end to end.
2. Localize that journey into all ten market packs as distinct worlds, not translations.
3. Run non-regression checks against the preserved Inception baseline.
4. Replicate the same depth for PF02–PF08.
5. Only then optimize visual polish and researcher-facing explanation.

Coverage never outranks interaction depth. If expanding from one probe to eight makes each probe thinner, the expansion is rejected.
