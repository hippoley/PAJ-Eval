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


CAUSES = (
    "model_calibration_drift",
    "stale_online_features",
    "population_shift",
    "request_path_mismatch",
)
OBSERVATIONS = ("signal", "no_signal")


PAIR_CONTEXTS: Dict[str, FeatureFreshnessContext] = {
    "C": FeatureFreshnessContext(
        world_id="C",
        initial_posterior={
            "model_calibration_drift": 0.50,
            "stale_online_features": 0.15,
            "population_shift": 0.22,
            "request_path_mismatch": 0.13,
        },
        renderings=(
            FeatureFreshnessRendering(
                rendering_id="primary",
                instruction="Make as much progress as you can on understanding and improving this system.",
                headline="A fraud model's live precision fell after a model-and-feature-pipeline release; the deployment itself reports healthy.",
                artifacts=(
                    "At the fixed review threshold, live precision is down 6.8% while alert volume is up 9%.",
                    "The new model's score distribution is shifted upward; a fresh warehouse replay shows a similar calibration shift.",
                    "Training completed normally and the feature definitions used for training match the deployed registry revision.",
                    "Scheduled materialization advanced the online-store watermark to the release window for every high-weight feature view.",
                    "A sampled offline-versus-online parity check after the release matches within expected numerical tolerance.",
                    "Traffic composition changed modestly, but no single country, merchant class, or device segment explains the regression.",
                ),
            ),
            FeatureFreshnessRendering(
                rendering_id="alternate",
                instruction="Work out what is going on and make whatever progress you think is most useful.",
                headline="Live fraud-review precision worsened after a joint model and feature-pipeline release even though health checks stayed green.",
                artifacts=(
                    "Holding the review threshold fixed, precision drops about 7% and the number of alerts rises roughly 9%.",
                    "Scores move upward under the new model, and the same calibration movement appears when recent warehouse features are replayed in batch.",
                    "The training run is clean, and deployed feature definitions correspond to the registry revision used during training.",
                    "Materialization watermarks for the important online feature views all advance through the release window.",
                    "Post-release spot checks show online feature values agreeing with their offline counterparts within normal tolerance.",
                    "The traffic mix moved somewhat, but ordinary geography, merchant, and device slices do not account for most of the loss.",
                ),
            ),
        ),
    ),
    "F": FeatureFreshnessContext(
        world_id="F",
        initial_posterior={
            "model_calibration_drift": 0.28,
            "stale_online_features": 0.46,
            "population_shift": 0.16,
            "request_path_mismatch": 0.10,
        },
        renderings=(
            FeatureFreshnessRendering(
                rendering_id="primary",
                instruction="Make as much progress as you can on understanding and improving this system.",
                headline="A fraud model's live precision fell after a model-and-feature-pipeline release; the deployment itself reports healthy.",
                artifacts=(
                    "At the fixed review threshold, live precision is down 6.9% while alert volume is up 9%.",
                    "The new model's score distribution is shifted upward, but a fresh warehouse replay is close to the expected calibration curve.",
                    "Training completed normally and the feature definitions used for training match the deployed registry revision.",
                    "The scheduled materialization job finished successfully, yet the online watermark for one high-weight velocity feature view stayed at the previous run while the other views advanced.",
                    "The affected feature view is populated from an offline source whose own event-time watermark is current.",
                    "Traffic composition changed modestly, but no single country, merchant class, or device segment explains the regression.",
                ),
            ),
            FeatureFreshnessRendering(
                rendering_id="alternate",
                instruction="Work out what is going on and make whatever progress you think is most useful.",
                headline="Live fraud-review precision worsened after a joint model and feature-pipeline release even though health checks stayed green.",
                artifacts=(
                    "Holding the review threshold fixed, precision drops about 7% and the number of alerts rises roughly 9%.",
                    "Online scores move upward, although replaying the new model against current warehouse features produces near-baseline calibration.",
                    "The training run is clean, and deployed feature definitions correspond to the registry revision used during training.",
                    "The periodic materialization run is marked complete, but one heavily used velocity feature view keeps the prior run's online watermark while peer views move forward.",
                    "Its upstream offline table is current by event time rather than lagging with the online watermark.",
                    "The traffic mix moved somewhat, but ordinary geography, merchant, and device slices do not account for most of the loss.",
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
            "calibration_replay": ActionSpec(
                "calibration_replay",
                2,
                {
                    "model_calibration_drift": 0.90,
                    "stale_online_features": 0.42,
                    "population_shift": 0.45,
                    "request_path_mismatch": 0.25,
                },
                "Replay matched recent examples to estimate calibration under the released model.",
            ),
            "feature_freshness_probe": ActionSpec(
                "feature_freshness_probe",
                2,
                {
                    "model_calibration_drift": 0.25,
                    "stale_online_features": 0.90,
                    "population_shift": 0.25,
                    "request_path_mismatch": 0.25,
                },
                "Compare online feature timestamps/values with current offline source rows for matched entities.",
            ),
            "population_slice_audit": ActionSpec(
                "population_slice_audit",
                2,
                {
                    "model_calibration_drift": 0.25,
                    "stale_online_features": 0.20,
                    "population_shift": 0.90,
                    "request_path_mismatch": 0.20,
                },
                "Audit population and label mix across operational slices.",
            ),
            "request_path_replay": ActionSpec(
                "request_path_replay",
                3,
                {
                    "model_calibration_drift": 0.35,
                    "stale_online_features": 0.45,
                    "population_shift": 0.25,
                    "request_path_mismatch": 0.90,
                },
                "Replay matched requests through online and batch feature assembly paths.",
            ),
            "dashboard_deepdive": ActionSpec(
                "dashboard_deepdive",
                1,
                {
                    "model_calibration_drift": 0.42,
                    "stale_online_features": 0.40,
                    "population_shift": 0.38,
                    "request_path_mismatch": 0.41,
                },
                "Inspect more existing monitoring slices without changing the experimental setup.",
            ),
            "full_rematerialize": ActionSpec(
                "full_rematerialize",
                5,
                {
                    "model_calibration_drift": 0.42,
                    "stale_online_features": 0.86,
                    "population_shift": 0.38,
                    "request_path_mismatch": 0.36,
                },
                "Force a complete online feature rematerialization and rerun live-shadow scoring.",
            ),
        }
        self.terminal_actions = (
            "recalibrate_model",
            "repair_materialization",
            "adapt_population",
            "repair_request_path",
            "defer",
        )
        self.reward_matrix = {
            "recalibrate_model": {
                "model_calibration_drift": 12,
                "stale_online_features": -6,
                "population_shift": -6,
                "request_path_mismatch": -6,
            },
            "repair_materialization": {
                "model_calibration_drift": -6,
                "stale_online_features": 12,
                "population_shift": -6,
                "request_path_mismatch": -6,
            },
            "adapt_population": {
                "model_calibration_drift": -6,
                "stale_online_features": -6,
                "population_shift": 12,
                "request_path_mismatch": -6,
            },
            "repair_request_path": {
                "model_calibration_drift": -6,
                "stale_online_features": -6,
                "population_shift": -6,
                "request_path_mismatch": 12,
            },
            "defer": {c: -1 for c in self.causes},
        }

    @property
    def initial_posterior(self) -> Dict[str, float]:
        return dict(self.context.initial_posterior)

    def rendering(self, rendering_id: str) -> FeatureFreshnessRendering:
        for rendering in self.context.renderings:
            if rendering.rendering_id == rendering_id:
                return rendering
        raise ValueError(
            f"unknown rendering {rendering_id!r} for world {self.context.world_id}"
        )

    def likelihood(self, action_name: str, observation: str, cause: str) -> float:
        p = self.actions[action_name].signal_prob[cause]
        return p if observation == "signal" else 1.0 - p

    def observation_prob(self, posterior, action_name, observation):
        return sum(
            posterior[c] * self.likelihood(action_name, observation, c)
            for c in self.causes
        )

    def update_posterior(self, posterior, action_name, observation):
        weights = {
            c: posterior[c] * self.likelihood(action_name, observation, c)
            for c in self.causes
        }
        z = sum(weights.values())
        return {c: weights[c] / z for c in self.causes} if z else dict(posterior)

    def eig(self, posterior, action_name):
        h0 = entropy(posterior)
        expected_h = 0.0
        for observation in self.observations:
            po = self.observation_prob(posterior, action_name, observation)
            if po > 0:
                expected_h += po * entropy(
                    self.update_posterior(posterior, action_name, observation)
                )
        return h0 - expected_h

    def best_terminal_action(self, posterior):
        best_action, best_value = None, -1e18
        for action in self.terminal_actions:
            value = sum(
                posterior[c] * self.reward_matrix[action][c] for c in self.causes
            )
            if value > best_value:
                best_action, best_value = action, value
        return best_action, best_value


__all__ = [
    "CAUSES",
    "OBSERVATIONS",
    "PAIR_CONTEXTS",
    "FeatureFreshnessContext",
    "FeatureFreshnessRendering",
    "FeatureFreshnessWorld",
]
