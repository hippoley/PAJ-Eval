# PAJ-Eval Journey Blueprints

These are implementation blueprints, not participant-facing copy. Each family is a three-world behavioral journey. The participant should experience ordinary software; family names remain researcher-side only.

The order below is deliberate: **seed → consequence → minimal intervention → near transfer → far transfer**. Every transfer world removes the previous domain vocabulary so that spontaneous structure, not verbal imitation, is measured.

---

## PF01 — downstream option structure

### Seed world
A consumer purchase where the cheaper headline option creates a downstream dependency.

**Ordinary objects**
- product list;
- owned-device inventory;
- buyer reviews;
- delivery / returns;
- free search;
- nested device detail.

**Consequence**
The cheaper controller reaches checkout and requires an additional bridge for two existing devices. The nominally cheaper option may become more expensive and more complex.

**Post-consequence actions**
- keep the original product;
- switch products;
- inspect the affected devices;
- return to search / reviews.

**Minimal intervention**
One sentence about a choice changing which choices remain later. No mention of compatibility, hidden cost, or downstream constraint.

### Near transfer
Two job offers. Headline salary favors one option; commute, contract, team mobility, and start-date constraints change the future option set.

### Far transfer
Time-constrained travel. A cheap late arrival changes ground transport, hotel, sleep, and next-morning attendance options.

### Confounds to separate
- general diligence;
- risk aversion;
- price sensitivity;
- preference for flexibility;
- simple “inspect everything” behavior.

### Key trajectory features
- downstream object opened before first commit;
- consequence-triggered revision;
- option-space object opened in near transfer without prompt;
- option-space object opened in far transfer without prompt;
- breadth vs targetedness of inspection.

---

## PF02 — competing causal frames

### Seed world
A production retrieval service drops in quality after a routine model/corpus refresh while the release pipeline remains green.

**Ordinary objects**
- quality dashboard;
- training / embedding run history;
- serving-index generations;
- corpus diff;
- online vs offline comparison;
- request / segment explorer.

**Competing explanations**
At least two causes remain plausible from headline evidence. One high-value observation sharply separates them; several attractive observations merely add volume.

**Consequence**
If the participant acts on the first plausible story, a later serving-generation comparison reveals that 18% of traffic is still pinned to an older index. If they inspect representation slices first, they see a real but non-diagnostic shift. The world never says which explanation is “correct.”

**Minimal intervention**
“Two stories can fit the same symptom; the next useful observation is the one that separates them.”

### Near transfer
A fulfillment dashboard shows late deliveries after a warehouse software change and a weather event. Objects include route mix, depot scan latency, carrier split, weather timeline, and one city-specific slice.

### Far transfer
A household energy / building-service anomaly: consumption rises after a tariff change and a thermostat firmware update. Objects include meter history, outside temperature, room schedules, firmware rollout, and occupancy. No software-debugging vocabulary is repeated.

### Confounds to separate
- generic thoroughness;
- “always inspect recent changes” heuristic;
- technical expertise;
- confirmation seeking.

### Key trajectory features
- number of hypotheses implicitly kept alive through inspection sequence;
- discriminating probe opened before escalation;
- first-story lock-in latency;
- transfer of comparison behavior across domains.

---

## PF03 — omitted evidence / provenance

### Seed world
A vendor comparison ranks one supplier first even though a critical evidence cell has no current source.

**Ordinary objects**
- comparison table;
- source notes;
- commercial contract;
- references;
- raw export;
- security / compliance appendix.

**Consequence**
If the participant chooses the current leader, a downstream review reveals that the missing evidence was copied from a prior cycle. If the source is requested, the ranking remains explicitly provisional rather than automatically corrected.

**Minimal intervention**
“What is absent can matter more than what is visible.”

### Near transfer
Apartment / workspace comparison. One seemingly best option has an attractive score built from a missing noise / commute / service-charge source.

### Far transfer
Selecting a long-term service provider. Testimonials and pricing are complete, but the failure / exit-condition evidence for the leading provider is missing.

### Confounds to separate
- distrust of top-ranked options;
- general source-checking habit;
- preference for raw data;
- risk aversion.

### Key trajectory features
- source/provenance object opened before commitment;
- explicit request for missing evidence;
- re-evaluation after provenance change;
- spontaneous provenance checking in transfer worlds.

---

## PF04 — anomaly triage

### Seed world
Conversion falls, traffic rises slightly, refunds stay flat, and support tickets increase after a release.

**Ordinary objects**
- funnel dashboard;
- release timeline;
- support-ticket themes;
- traffic mix;
- payment health;
- segment drill-down.

**Consequence**
Opening support-ticket detail reveals a concentration on the post-release confirmation flow; traffic is genuinely changing but not along the failure path.

**Minimal intervention**
“Several things can move together without belonging to the same failure path.”

### Near transfer
A delivery operation has rising delay, normal cancellation, one depot’s scan lag, and a simultaneous regional weather event.

### Far transfer
A travel day has a gate change, a rail disruption, hotel inventory drop, and a localized road closure. The task is not “find the anomaly” but decide which signal deserves first investigation.

### Confounds to separate
- recency bias;
- magnitude bias;
- release-change heuristic;
- support-ticket salience;
- general breadth of browsing.

### Key trajectory features
- triage order;
- causal-path objects opened before non-path anomalies;
- time to abandon a tempting but irrelevant signal;
- transfer of triage ordering.

---

## PF05 — experiment choice under real constraints

### Seed world
A launch decision has three competing explanations and budget for one meaningful experiment.

**Ordinary objects**
- hypothesis notebook;
- cheap broad test;
- expensive discriminating intervention;
- large observational sample;
- budget / time ledger;
- prior results.

**Consequence**
Running a test irreversibly consumes budget and reveals an ambiguous result. The biggest experiment is not necessarily the most decision-relevant.

**Minimal intervention**
“Information is valuable only when it can change the decision enough to justify its cost.”

### Near transfer
A manufacturing / quality process with one shift left before a production decision. Tests differ in downtime, sample size, and ability to separate two causes.

### Far transfer
An unfamiliar field operation where the participant can inspect, sample, or intervene once before committing resources.

### Confounds to separate
- preference for largest sample;
- cheap-first heuristic;
- activity bias;
- generic cost aversion.

### Key trajectory features
- experiment selected relative to explicit budget;
- unused budget;
- whether result triggers revision;
- value-of-information structure reused across domains.

---

## PF06 — stopping under delayed failure

### Seed world
A mitigation appears successful immediately, but similar incidents have sometimes failed after 25–40 minutes. Every additional check consumes rollback time.

**Ordinary objects**
- immediate metrics;
- incident history;
- delayed checks;
- check cost;
- rollback status;
- affected-shard detail.

**Consequence**
T+15 remains healthy; T+30 reveals a small growing error cluster while the rollback window has shrunk.

**Minimal intervention**
“Stopping and continuing both have costs; the question is whether remaining uncertainty can still reverse the action.”

### Near transfer
A delayed shipment recovery looks normal after rerouting, but a later depot cutoff can still break next-day delivery.

### Far transfer
A home / building automation recovery appears normal immediately, while a scheduled control cycle can re-trigger the failure later.

### Confounds to separate
- always-wait strategy;
- risk aversion;
- impatience;
- sunk-cost behavior.

### Key trajectory features
- stopping time;
- history inspected before stopping;
- delayed check sequence;
- rollback-window awareness;
- transfer of stopping discipline.

---

## PF07 — wrong problem / objective challenge

### Seed world
An AI assistant produces a polished, internally coherent plan to optimize a supplied metric. The original request and stakeholder complaints point to a different objective.

**Ordinary objects**
- assistant plan;
- original request;
- stakeholder note;
- metric definition;
- operational constraints;
- prior experiment outcomes.

**Consequence**
Following the plan improves the metric while worsening the complaint that motivated the task. Reframing changes the available interventions.

**Minimal intervention**
“A strong solution can still be strong for the wrong problem.”

### Near transfer
A support-automation proposal reduces average handle time but increases repeat contacts and unresolved cases.

### Far transfer
A scheduling / policy optimization improves utilization while violating the actual service objective for a vulnerable subgroup. Keep the scenario non-medical and non-political; the issue is objective mismatch, not ideology.

### Confounds to separate
- generalized distrust of AI;
- anti-metric sentiment;
- preference for stakeholder narratives;
- contrarianism.

### Key trajectory features
- original-request / objective object opened before execution;
- explicit reframe action;
- whether the participant seeks objective definition in transfer worlds without prompt;
- whether polishedness changes inspection behavior.

---

## PF08 — spontaneous opening in sparse worlds

PF08 is the hardest family and should not reuse a learned vocabulary. It exists to test whether investigative structure appears without being named.

### Seed world
A sparse operational workspace contains recent records, affected groups, temporal changes, one hard constraint, and external context. No diagnostic question is supplied.

**Ordinary objects**
- current records;
- history;
- people / groups;
- constraints;
- external context;
- nested record detail.

**Consequence**
Opening different objects gradually reveals relations such as `record → group → change`. No object says “cause,” “constraint,” “missing evidence,” or any previous family label.

**Minimal intervention**
None in the confirmatory version. PF08 is itself a transfer endpoint. In exploratory versions, a neutral “you may open anything you would normally inspect” instruction is allowed.

### Near transfer
An event-planning workspace with sparse vendor changes, attendee groups, schedule constraints, and external disruptions.

### Far transfer
An unfamiliar maintenance / operations workspace with different visual structure and vocabulary.

### Confounds to separate
- click-all behavior;
- UI salience;
- chronological browsing;
- generic curiosity.

### Key trajectory features
- first object category opened;
- number of cross-object relations discovered;
- targeted revisits after a relation appears;
- whether opening sequence compresses across repeated unfamiliar domains;
- omission pattern.

---

# Shared implementation rules

## Participant layer
- ordinary application names only;
- no PF IDs;
- no construct titles;
- no correctness feedback;
- no forced research path;
- free backtracking;
- locally coherent distractors;
- terminal action always available.

## Event layer
Record at least:
- world entry;
- top-level object open;
- nested detail open;
- search query event without persisting sensitive free text unless explicitly consented;
- state-changing action;
- consequence exposure;
- post-consequence action;
- transfer-world entry;
- terminal commit;
- elapsed time and sequence number.

## Localization layer
Every full journey is built from a market pack. Do not assume the same transport mode, employment framing, currency, city scale, return policy language, or interaction idiom across markets. Match **affordance and cue strength**, not literal words.

## Research layer
Derived features and evaluations remain versioned and replayable. Any scoring model that cannot explain which raw events support a feature is rejected.
