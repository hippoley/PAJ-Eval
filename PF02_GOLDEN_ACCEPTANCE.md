# PF02 Golden Journey Acceptance Gate

PF02 is the first family built after the PF01 golden reference. Its purpose is to test whether a participant keeps more than one explanation alive long enough to seek an observation that separates them, and whether that investigative structure reappears in unrelated domains after the one-sentence intervention.

The participant-facing journey must never use the research-family name or language such as “competing causal frames,” “discriminating evidence,” “posterior,” or “correct hypothesis.”

## Journey shape

1. **Seed — retrieval incident.** Quality falls after a routine refresh while the release pipeline is green. Model/embedding drift and serving-index mismatch are both ordinary plausible stories.
2. **Ordinary consequence.** The participant may act immediately. A provisional mitigation changes the live monitor but does not narrate which story is right. The world preserves evidence that can separate explanations.
3. **Minimal intervention.** One sentence only: two stories can fit the same symptom; the next useful observation is the one that separates them.
4. **Near transfer — fulfillment delay.** A warehouse software change and a weather event overlap in time. Depot scans, carrier mix, routes, weather, and city slices create multiple plausible explanations.
5. **Far transfer — household/building energy anomaly.** Consumption rises after both a tariff change and thermostat firmware rollout. Meter history, weather, schedules, firmware, occupancy, and room/zone detail are available without software-debugging vocabulary.

## Minimum participant interaction depth

Every world must expose at least five ordinary top-level objects and at least two nested evidence paths. A participant must be able to act before inspecting them. No required research path and no correctness feedback.

### Seed world

Required top-level objects:
- overview / live quality;
- request or query slices;
- serving/index generations;
- corpus changes;
- release history;
- request explorer.

Required nested evidence:
- serving generation comparison;
- slice/request detail.

Required state changes:
- provisional mitigation;
- post-action monitor;
- possibility to inspect or revise after the consequence.

Failure if the UI simply says “18% is on the old index” before the participant chooses to inspect the relevant object.

### Near transfer

Required top-level objects:
- delivery overview;
- depot scan timing;
- carrier mix;
- routes;
- weather timeline;
- city/zone slices.

At least two ordinary actions must remain plausible from headline evidence. A provisional action must produce a partial outcome, preserving a useful distinction between local weather/route effects and system-wide scan/process effects.

### Far transfer

Required top-level objects:
- energy usage;
- outside weather;
- room/zone schedules;
- thermostat/firmware history;
- occupancy;
- tariff/billing context.

The participant must be able to make a provisional change, see the next interval of data, inspect room/time detail, and revise before the final action. The world must not reuse “generation,” “index,” “release,” “carrier,” or other seed/near-transfer diagnostic vocabulary as a cue.

## Confounds to preserve and measure

PF02 must remain capable of distinguishing the target structure from:
- generic thoroughness;
- “always inspect the latest change” behavior;
- technical expertise in retrieval systems;
- generic risk aversion;
- opening every object;
- simple preference for rollback/reversal.

Therefore the world needs attractive but non-separating evidence as well as a smaller number of observations that materially separate stories.

## Localization requirements

Ten market packs remain explicit: US, CN, TW, JP, KR, ES, FR, DE, BR, RU.

The technical seed may preserve globally recognizable software artifacts such as NDCG or index-generation IDs, but participant copy, button verbs, dates/times, operational examples, fulfillment locations, weather context, energy tariff units, and household/building language must be localized.

Near/far worlds must use plausible local geography and conditions. Structural comparability is the invariant; literal weather, currency, city, and utility details are not.

## Raw event distinctions

Preserve at least:
- `open_object`;
- `open_detail`;
- `provisional_action`;
- `post_action_check`;
- `post_consequence_action`;
- `minimal_intervention`;
- `commit`;
- `session_complete`.

Useful candidate replay features include:
- evidence breadth before first action;
- whether a separating object is opened before action;
- time to first-story lock-in;
- number of revisions after partial outcomes;
- near-transfer separating evidence opened without prompt;
- far-transfer separating evidence opened without prompt;
- targeted nested evidence / total browsing ratio.

These are descriptive features, not a validated score.

## Kill criteria

Revise PF02 before public research use if:
- the intended cause can be inferred from one highlighted card;
- one action is visually marked as the safe/correct choice;
- the minimal intervention names the object to click;
- the fulfillment and energy worlds feel like reskinned incident dashboards;
- a locale’s weather, logistics, or utility facts are obviously implausible;
- selecting an action immediately ends a world before the participant can observe and revise;
- raw replay cannot reconstruct which evidence was available before each action.
