from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .world import ActionSpec, entropy


@dataclass(frozen=True)
class FeatureFreshnessRendering:
    rendering_id: str
    instruction: str
    headline: str
    artifacts: Tuple[str, ...]


@dataclass(frozen=True)
class FeatureFreshnessContext:
    world_id: str
    initial_posterior: Dict[str, float]
    renderings: Tuple[FeatureFreshnessRendering, ...]


CAUSES = ("model_calibration_drift", "stale_online_features", "population_shift", "request_path_mismatch")
OBSERVATIONS = ("signal", "no_signal")

PAIR_CONTEXTS: Dict[str, FeatureFreshnessContext] = {
    "C": FeatureFreshnessContext(
        world_id="C",
        initial_posterior={"model_calibration_drift": 0.50, "stale_online_features": 0.15, "population_shift": 0.22, "request_path_mismatch": 0.13},
        renderings=(
            FeatureFreshnessRendering(
                "primary",
                "You have inherited this system after a routine release. Decide what you would do next.",
                "Live fraud-review precision is worse after a model-and-feature release; deployment health is green.",
                (
                    "At the fixed review threshold, precision is down 6.8% while alert volume is up 9%.",
                    "The new model's live score distribution is shifted upward; a recent warehouse replay shows a similar shift.",
                    "Training completed normally and the deployed feature definitions match the registry revision used for training.",
                    "The scheduled feature publication job completed in its normal runtime range and reports the expected entity coverage.",
                    "A routine post-release spot check of several online feature values agrees with warehouse values within normal tolerance.",
                    "Traffic composition moved modestly, but ordinary geography, merchant, and device slices do not explain most of the loss.",
                ),
            ),
            FeatureFreshnessRendering(
                "alternate",
                "You are taking over this system after a routine release. What would you do next?",
                "Fraud-review precision worsened after the latest model-and-feature release although health checks stayed green.",
                (
                    "Holding the review threshold fixed, precision drops about 7% and alert volume rises roughly 9%.",
                    "Scores move upward under the new model, and recent warehouse replay shows a similar calibration movement.",
                    "The training run is clean and deployed feature definitions correspond to the training registry revision.",
                    "The regular feature publication run finishes in its usual time range and reports expected entity coverage.",
                    "A small routine sample after release shows online values agreeing with warehouse values within normal tolerance.",
                    "The traffic mix moved somewhat, but standard geography, merchant, and device slices account for little of the loss.",
                ),
            ),
        ),
    ),
    "F": FeatureFreshnessContext(
        world_id="F",
        initial_posterior={"model_calibration_drift": 0.28, "stale_online_features": 0.46, "population_shift": 0.16, "request_path_mismatch": 0.10},
        renderings=(
            FeatureFreshnessRendering(
                "primary",
                "You have inherited this system after a routine release. Decide what you would do next.",
                "Live fraud-review precision is worse after a model-and-feature release; deployment health is green.",
                (
                    "At the fixed review threshold, precision is down 6.9% while alert volume is up 9%.",
                    "The live score distribution is shifted upward, but replaying the released model on recent warehouse features is close to the previous calibration curve.",
                    "Training completed normally and the deployed feature definitions match the registry revision used for training.",
                    "The scheduled feature publication job completed in its normal runtime range and reports the expected entity coverage.",
                    "In the routine post-release sample, most online values match warehouse values; one high-weight velocity feature is absent from that sample because its entity keys did not overlap the check set.",
                    "Traffic composition moved modestly, but ordinary geography, merchant, and device slices do not explain most of the loss.",
                ),
            ),
            FeatureFreshnessRendering(
                "alternate",
                "You are taking over this system after a routine release. What would you do next?",
                "Fraud-review precision worsened after the latest model-and-feature release although health checks stayed green.",
                (
                    "Holding the review threshold fixed, precision drops about 7% and alert volume rises roughly 9%.",
                    "Online scores move upward, although the released model run against current warehouse features stays near the prior calibration curve.",
                    "The training run is clean and deployed feature definitions correspond to the training registry revision.",
                    "The regular feature publication run finishes in its usual time range and reports expected entity coverage.",
                    "Routine parity sampling covers the common feature views; a heavily weighted velocity feature is not represented because none of its entity keys landed in the sample.",
                    "The traffic mix moved somewhat, but standard geography, merchant, and device slices account for little of the loss.",
                ),
            ),
        ),
    ),
}


class FeatureFreshnessWorld:
    """Cross-domain counterfactual for testing transfer beyond vector-index trivia."""
    causes = CAUSES
    observations = OBSERVATIONS

    def __init__(self, world_id: str, budget: int = 7):
        if world_id not in PAIR_CONTEXTS:
            raise ValueError(f"unknown feature-freshness world: {world_id}")
        self.context = PAIR_CONTEXTS[world_id]
        self.budget = budget
        self.actions: Dict[str, ActionSpec] = {
            "calibration_replay": ActionSpec("calibration_replay", 2, {"model_calibration_drift": .90, "stale_online_features": .42, "population_shift": .45, "request_path_mismatch": .25}, "Replay matched recent examples to estimate calibration under the released model."),
            "feature_freshness_probe": ActionSpec("feature_freshness_probe", 2, {"model_calibration_drift": .25, "stale_online_features": .90, "population_shift": .25, "request_path_mismatch": .25}, "Compare online feature timestamps/values with current offline source rows for matched entities."),
            "population_slice_audit": ActionSpec("population_slice_audit", 2, {"model_calibration_drift": .25, "stale_online_features": .20, "population_shift": .90, "request_path_mismatch": .20}, "Audit population and label mix across operational slices."),
            "request_path_replay": ActionSpec("request_path_replay", 3, {"model_calibration_drift": .35, "stale_online_features": .45, "population_shift": .25, "request_path_mismatch": .90}, "Replay matched requests through online and batch feature assembly paths."),
            "dashboard_deepdive": ActionSpec("dashboard_deepdive", 1, {"model_calibration_drift": .42, "stale_online_features": .40, "population_shift": .38, "request_path_mismatch": .41}, "Inspect more existing monitoring slices without changing the experimental setup."),
            "full_rematerialize": ActionSpec("full_rematerialize", 5, {"model_calibration_drift": .42, "stale_online_features": .86, "population_shift": .38, "request_path_mismatch": .36}, "Force a complete online feature rematerialization and rerun live-shadow scoring."),
        }
        self.terminal_actions = ("recalibrate_model", "repair_materialization", "adapt_population", "repair_request_path", "defer")
        self.reward_matrix = {
            "recalibrate_model": {"model_calibration_drift": 12, "stale_online_features": -6, "population_shift": -6, "request_path_mismatch": -6},
            "repair_materialization": {"model_calibration_drift": -6, "stale_online_features": 12, "population_shift": -6, "request_path_mismatch": -6},
            "adapt_population": {"model_calibration_drift": -6, "stale_online_features": -6, "population_shift": 12, "request_path_mismatch": -6},
            "repair_request_path": {"model_calibration_drift": -6, "stale_online_features": -6, "population_shift": -6, "request_path_mismatch": 12},
            "defer": {c: -1 for c in self.causes},
        }

    @property
    def initial_posterior(self) -> Dict[str, float]: return dict(self.context.initial_posterior)

    def rendering(self, rendering_id: str) -> FeatureFreshnessRendering:
        for rendering in self.context.renderings:
            if rendering.rendering_id == rendering_id: return rendering
        raise ValueError(f"unknown rendering {rendering_id!r} for world {self.context.world_id}")

    def likelihood(self, action_name: str, observation: str, cause: str) -> float:
        p = self.actions[action_name].signal_prob[cause]
        return p if observation == "signal" else 1.0 - p

    def observation_prob(self, posterior, action_name, observation): return sum(posterior[c] * self.likelihood(action_name, observation, c) for c in self.causes)

    def update_posterior(self, posterior, action_name, observation):
        weights = {c: posterior[c] * self.likelihood(action_name, observation, c) for c in self.causes}
        z = sum(weights.values())
        return {c: weights[c] / z for c in self.causes} if z else dict(posterior)

    def eig(self, posterior, action_name):
        h0 = entropy(posterior); expected_h = 0.0
        for observation in self.observations:
            po = self.observation_prob(posterior, action_name, observation)
            if po > 0: expected_h += po * entropy(self.update_posterior(posterior, action_name, observation))
        return h0 - expected_h

    def best_terminal_action(self, posterior):
        best_action, best_value = None, -1e18
        for action in self.terminal_actions:
            value = sum(posterior[c] * self.reward_matrix[action][c] for c in self.causes)
            if value > best_value: best_action, best_value = action, value
        return best_action, best_value


__all__ = ["CAUSES", "OBSERVATIONS", "PAIR_CONTEXTS", "FeatureFreshnessContext", "FeatureFreshnessRendering", "FeatureFreshnessWorld"]
