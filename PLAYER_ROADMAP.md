# Probe Player development sequence

The library now has PF01-PF08 playable seeds. Development should deepen families rather than multiply shallow cards.

Next sequence:

1. PF02 first: connect the existing retrieval R/S counterfactual world to Probe Player and replace placeholder evidence with deterministic latent-world observations.
2. PF05 second: expose the existing oracle/value machinery through a natural experiment-selection world and compute ERU/regret from the same session trace.
3. PF07 third: add an assistant-supplied plausible frame, then a no-AI wrong-problem transfer world to operationalize epistemic control.
4. PF08 fourth: compose held-out worlds from PF02/PF05/PF07 without target vocabulary and measure spontaneous opening.
5. PF03/PF04/PF06: grow as discriminant-validity families targeting omitted evidence, salience, and stopping.
6. PF01: retain as the accessible public onboarding probe, but add a negative-transfer world so downstream-option seeking is not rewarded everywhere.

For every step: automated invariant tests -> developer dogfood -> naive UX pilot -> counterfactual validity -> only then treatment testing.