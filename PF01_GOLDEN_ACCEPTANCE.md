# PF01 Golden Challenge Acceptance Gate

This document is the release gate for the first full golden-depth journey. It is intentionally stricter than “the page renders” or “the intended answer can be found.”

PF01 is complete only when the participant experience, behavioral measurement, localization, and replay all survive this checklist.

## 1. Participant experience

The participant should feel that they are using three ordinary applications, not moving through a psychometric test.

### Seed world — purchase

Required:

- five ordinary top-level objects: products, owned devices, reviews, delivery/returns, free search;
- nested device detail;
- either headline product can be selected immediately;
- both product paths produce an ordinary downstream consequence;
- Lite exposes the compatibility / bridge chain;
- Pro exposes the same-day-stock / pickup chain;
- consequence is visible as changed world state, never as “you missed a hidden constraint” narration;
- after the consequence the participant can keep, switch, or inspect;
- the structural intervention remains one short sentence and is true for the consequence actually experienced.

Failure conditions:

- one product path skips the consequence but still receives the intervention;
- the interface names the research construct;
- opening owned devices is mandatory;
- the user cannot reverse course after checkout changes.

### Near transfer — job offers

Required:

- six ordinary top-level objects;
- both offers are actionable without opening any additional evidence;
- contract, team, and role-mobility details are separate nested objects;
- commute and start-date information remain ordinary navigable objects;
- no shopping / compatibility vocabulary is reused as a transfer cue;
- final choice remains possible under incomplete information.

Primary observable is not which offer is chosen. It is whether option-structure evidence is opened spontaneously and how targeted that inspection is relative to general browsing.

### Far transfer — time-constrained travel

Required:

- five ordinary top-level objects;
- transport / hotel / morning constraints can be inspected before booking;
- booking first creates a **provisional** state, not an immediate terminal answer;
- the ordinary booking summary makes downstream arrival consequences visible;
- participant may confirm, switch timing, open the arrival plan, or return to fares;
- arrival plan contains three independent nested evidence paths;
- switching after the booking consequence is recorded separately from ordinary browsing;
- final commit remains possible without opening the nested evidence.

Failure conditions:

- the final world is a static two-button answer card;
- selecting a fare ends the task before a consequence can be experienced;
- nested evidence is auto-opened;
- the “better” action is visually marked as correct.

## 2. Localization gate

Each locale is an explicit market world, not a translated skin.

Current packs:

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

For every pack verify:

- displayed Pro price and consequence copy agree exactly;
- route, arrival time, station / airport, and downstream transport assumptions do not contradict each other;
- the job-offer commute and work-location language is plausible for the named market;
- reviews and buttons sound like native product UI rather than translated research prose;
- the late / constrained option is structurally comparable without requiring the same literal clock time;
- the number of top-level and nested affordances is invariant even when nouns and prices differ;
- reading load is not obviously doubled or halved relative to other packs.

At least one native or near-native reviewer should inspect every market pack before a cross-market claim is made. Automated tests catch structural and factual drift; they do not certify cultural naturalness.

## 3. Behavioral event contract

The local golden challenge must preserve these distinctions:

- `open_object` — ordinary top-level navigation;
- `open_detail` — nested evidence voluntarily opened;
- `search_query` — self-directed information request;
- `provisional_commit` — action taken before the world has fully settled;
- `post_consequence_action` — revision / keep / inspect after a consequence becomes visible;
- `minimal_intervention` — structural cue exposure;
- `commit` — terminal choice within a transfer world;
- `session_complete` — journey completion.

Do not collapse these into a single “click” event. Timing and world identity remain attached to every event.

## 4. Descriptive features for pilot review

These are **descriptive replay features**, not a participant score and not a validated latent measure.

Useful first-pass summaries:

1. `seed_precommit_evidence_count` — ordinary evidence opened before the seed provisional commit.
2. `seed_nested_evidence_count` — nested device / pickup evidence opened.
3. `seed_revision_after_consequence` — whether the product path changes after consequence.
4. `near_transfer_nested_count` — contract / team / mobility details opened before career commit.
5. `near_transfer_breadth` — number of distinct career top-level objects opened.
6. `far_precommit_breadth` — travel objects opened before the first fare selection.
7. `far_arrival_plan_opened` — whether the participant voluntarily opens the post-selection arrival plan.
8. `far_nested_count` — transport / hotel / morning nested details opened.
9. `far_revision_after_consequence` — whether timing is switched after the booking state becomes visible.
10. `inspection_targetedness` — nested / discriminating evidence relative to total browsing.

No single feature is sufficient. In particular, “opened many things” must remain distinguishable from transfer of a useful investigative structure.

## 5. Human pilot failure modes

The journey should be revised before public research use if pilot reviewers repeatedly report any of the following:

- they can name the intended construct from the participant copy before the consequence;
- the correct-looking action is obvious from typography or color rather than evidence;
- the intervention simply tells them which object to inspect next;
- the career or travel worlds feel like disguised versions of the shopping world;
- people inspect every object because the interface looks like a checklist;
- a locale contains facts a local user would immediately recognize as implausible;
- users cannot tell whether an action is provisional or final;
- the raw event sequence cannot reconstruct what world state the participant saw.

## 6. Public-showcase gate

The public challenge should be shown as a playable artifact first and explained second.

Recommended order for an external researcher:

1. open the challenge with no construct explanation;
2. complete the three-world journey;
3. inspect the raw trajectory replay;
4. only then read the research hypothesis and measurement notes;
5. invite the strongest objection or alternative explanation.

The purpose is not to make the benchmark look finished. The purpose is to make the underlying experimental question hard to ignore and easy to challenge.
