# Playable Probe v2 — HCI contract

This document describes participant-facing interaction requirements. It is an instrument contract, not a claim about human effects.

## Design goal

The interface should let inquiry happen rather than ask participants to describe an inquiry that the interface has already framed for them.

The participant experience is a system handoff, not a quiz. The interface must make it possible to notice, inspect, update, stop, and act while minimizing cues about the benchmark's latent causal model.

## Interaction invariants

1. **No diagnostic menu before the spontaneous opening is locked.** The first substantive action is a free response to: `What would you do next, and why?`
2. **Progressive disclosure.** Initial evidence is limited to information plausibly visible at handoff. Investigation-specific evidence appears only after the participant chooses to acquire it.
3. **Action has consequence.** Every investigation consumes visible budget and produces a world-dependent observation.
4. **Recognition is not opening.** The event log preserves the pre-console snapshot separately from all menu-guided behavior.
5. **No correctness feedback.** The participant never sees oracle values, posterior probabilities, latent causes, scores, or a success/failure animation.
6. **Deferral is first-class.** The UI must not force a diagnosis when evidence is insufficient.
7. **Omitted actions are measurable.** A participant can record an investigation the interface failed to offer.
8. **Instrument critique comes last.** Realism, ambiguity, and leakage questions appear only after the terminal decision.
9. **Local-first privacy.** No participant response is transmitted automatically in the pilot build.
10. **Fail closed.** If world/action/result mappings are incomplete, the probe must refuse to start.

## HCI changes from v0.1

### 1. Reduce questionnaire feel
- Treat the system state as a work surface rather than a survey card.
- Keep the first-move editor visually adjacent to the system state.
- Move research-language and instrument-language out of the task surface.

### 2. Preserve attentional choice
- Do not visually highlight the clue that differs between counterfactual worlds.
- Keep evidence rows typographically equivalent.
- Avoid warning colors on causal clues.
- Investigation buttons use the same visual weight before selection.

### 3. Make state legible without teaching strategy
- Persistent budget indicator.
- Plain chronological evidence trail.
- Clear distinction between `observed at handoff`, `actively investigated`, and `working notes`.
- Do not display suggested hypotheses, confidence meters, causal categories, or recommended next steps.

### 4. Lower interaction cost
- One primary action per phase.
- Keyboard-accessible controls and visible focus states.
- Minimum 44px touch targets.
- Responsive one-column layout on narrow screens.
- Preserve participant text until explicit restart.

### 5. Prevent accidental data corruption
- First move becomes immutable after confirmation.
- Investigation actions are idempotent: the same probe cannot be purchased twice.
- Terminal decision requires explicit confirmation in v2.
- Export is available only after the instrument-check step.

## Behavioral event schema

Minimum events:

- `session_started`
- `opening_locked` with elapsed time and text length
- `investigation_selected` with action, cost, budget-before, elapsed time
- `evidence_revealed` with action and observation ID
- `terminal_selected` with remaining budget and elapsed time
- `instrument_feedback_submitted`
- `response_exported`

Do not infer cognition from hover or pointer movement in the pilot. Click/order/time are sufficient until measurement validity is established.

## Self-validation checklist

Before a build is pilotable:

- all worlds expose the same action labels and costs;
- every action has one observation in every world;
- initial evidence contains no latent-cause identifiers;
- the action menu is absent from the DOM-visible task surface before `opening_locked`;
- no participant-facing string contains `oracle`, `posterior`, `correct`, `wrong`, or a latent cause name;
- budget cannot become negative;
- terminal decision is possible without exhausting budget;
- exported JSON separates pre-console text from post-menu trajectory;
- restarting creates a new randomized condition and clears the previous state.

## Evaluation interpretation

The UI records two distinct constructs:

**Spontaneous Diagnostic Opening (SDO):** what problem representation appears before candidate investigations are supplied.

**Downstream inquiry / decision quality:** what evidence the participant chooses after the console exists, how they sequence investigations, when they stop, and what terminal action they take.

A participant can have weak SDO and strong downstream performance. That divergence is data; the interface must not collapse it into a single score.
