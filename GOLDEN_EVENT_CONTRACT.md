# Golden Challenge Event Contract

This contract is for the local-only Golden-depth challenge suite. It exists so PF01–PF08 can be frozen into one replayable instrument later without losing family-specific behavior.

## Shared journey events

Every family records the following semantic milestones where they apply:

- `session_start` — local journey begins; includes locale and market.
- `open_object` — first opening of an ordinary top-level object.
- `open_detail` — opening nested evidence inside an object.
- `provisional_action` or PF01 `provisional_commit` — an ordinary action is selected before the world is finalized.
- `consequence_exposed` — the world shows the state change or downstream consequence caused by that provisional action.
- `post_consequence_action` — participant inspects more, changes the provisional action, or otherwise responds after consequence exposure.
- `commit` — current world is finalized.
- `session_complete` — journey ends.

PF01 now records an explicit seed-world `commit`; consequence exposure is explicit rather than inferred from screen order.

PF02 retains `post_action_check` as a family-specific diagnostic event, but also emits `consequence_exposed` so downstream replay has one common semantic milestone.

## Intervention / transfer events

PF01–PF07:
- `minimal_intervention` — exactly one structural sentence between seed and near transfer.
- It must never contain a correct answer, construct label, PF identifier, or specific target object.

PF08 confirmatory journey:
- **must not emit `minimal_intervention`**.
- `workspace_transition` is a neutral surface transition only.

## Family-specific evidence events

These remain additive; they do not replace the shared milestones.

- PF02: `post_action_check`, serving-generation comparison.
- PF03: `request_missing_evidence`.
- PF04: first triage object / nested incident evidence.
- PF05: `experiment_run`, cost, budget before/after, remaining slot.
- PF06: `delayed_check`, elapsed virtual time, rollback/recovery window.
- PF07: `objective_artifact_opened` and pre-action objective-artifact state.
- PF08: `first_open_category`, `revisit_object`, `revisit_detail`, `relation_discovered`, omissions at commit.

## Required event envelope at freeze time

Before the Golden suite is reattached to research persistence, all events will be normalized into the canonical envelope:

```json
{
  "seq": 1,
  "t_ms": 1200,
  "event": "open_object",
  "world": "seed",
  "target": "nav_2",
  "locale": "en",
  "market": "US",
  "instrument_version": "golden-suite-v1"
}
```

Family-specific state belongs in additional explicit fields. The normalizer must not destroy the original local raw event.

## Ordering invariants

For each world:

1. any evidence opening may occur before action, or no evidence may be opened at all;
2. provisional action precedes consequence exposure;
3. consequence exposure precedes a post-consequence revision when one occurs;
4. commit is terminal for that world;
5. transfer-world entry occurs only after the preceding world commits.

PF08 additionally requires that no object is auto-opened on world entry. First-open category must be a participant action, not a renderer side effect.

## Persistence boundary

Golden journeys remain local-only until:
- all eight families pass the cross-family Golden Suite contract;
- participant-visible construct leakage checks pass;
- ten-market pack coverage passes;
- event normalization is versioned;
- consent and durable submission semantics are reattached deliberately;
- authenticated researcher replay is validated end to end.

Do not map local Golden preview runs onto the legacy canonical PF ingestion contract merely to make them persist.
