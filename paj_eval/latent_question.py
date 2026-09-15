from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .world import ActionSpec, entropy


@dataclass(frozen=True)
class LatentQuestionRendering:
    rendering_id: str
    instruction: str
    headline: str
    artifacts: Tuple[str, ...]


@dataclass(frozen=True)
class LatentQuestionContext:
    world_id: str
    initial_posterior: Dict[str, float]
    renderings: Tuple[LatentQuestionRendering, ...]


CAUSES = (
    "representation_drift",
    "evaluation_path_artifact",
    "corpus_shift",
    "serving_mismatch",
)
OBSERVATIONS = ("signal", "no_signal")


PAIR_CONTEXTS: Dict[str, LatentQuestionContext] = {
    "R": LatentQuestionContext(
        world_id="R",
        initial_posterior={
            "representation_drift": 0.60,
            "evaluation_path_artifact": 0.18,
            "corpus_shift": 0.14,
            "serving_mismatch": 0.08,
        },
        renderings=(
            LatentQuestionRendering(
                rendering_id="primary",
                instruction="Make as much progress as you can on understanding and improving this system.",
                headline="Offline retrieval quality fell after an encoder refresh; training itself looks clean.",
                artifacts=(
                    "NDCG@10 is down 7.0% and recall@50 is down 5.6% against the previous encoder.",
                    "Embedding centroids moved by about 0.11 cosine distance and nearest-neighbor turnover increased to 19%.",
                    "Training loss, negative-sampling mix, and optimizer telemetry show no obvious instability.",
                    "One evaluation shard is somewhat worse than the others (-8.2% versus -6.5%), but that shard showed comparable dispersion in two earlier releases.",
                    "A fixed replay of stored candidate scores reproduces the aggregate metric within 0.3 NDCG points across shard assignments.",
                    "A small online canary is also down, although its confidence interval is wide.",
                ),
            ),
            LatentQuestionRendering(
                rendering_id="alternate",
                instruction="Work out what is going on and make whatever progress you think is most useful.",
                headline="A refreshed retrieval encoder looks worse offline even though the training run appears normal.",
                artifacts=(
                    "Compared with the previous encoder, NDCG@10 falls by about 7% and recall@50 by about 5.5%.",
                    "The refreshed embedding space shows a centroid displacement near 0.11 cosine and roughly one-fifth neighbor turnover.",
                    "No clear failure appears in the loss curve, sampler composition, or optimizer telemetry.",
                    "A single evaluation shard is modestly worse than its peers, but similar shard-level spread existed before this release.",
                    "Replaying stored candidate scores under different shard assignments changes aggregate NDCG by no more than about 0.3 points.",
                    "The online canary trends downward too, but the sample is still small.",
                ),
            ),
        ),
    ),
    "E": LatentQuestionContext(
        world_id="E",
        initial_posterior={
            "representation_drift": 0.28,
            "evaluation_path_artifact": 0.52,
            "corpus_shift": 0.12,
            "serving_mismatch": 0.08,
        },
        renderings=(
            LatentQuestionRendering(
                rendering_id="primary",
                instruction="Make as much progress as you can on understanding and improving this system.",
                headline="Offline retrieval quality fell after an encoder refresh; training itself looks clean.",
                artifacts=(
                    "NDCG@10 is down 7.1% and recall@50 is down 5.4% against the previous encoder.",
                    "Embedding centroids moved by about 0.10 cosine distance and nearest-neighbor turnover increased to 18%.",
                    "Training loss, negative-sampling mix, and optimizer telemetry show no obvious instability.",
                    "One evaluation shard is markedly worse (-11.0% versus -4.9% elsewhere), even though it mixes the same broad query domains as the other shards.",
                    "On a 2,000-query fixed replay, raw candidate scores are stable, but aggregate NDCG moves by about 1.2 points when the same examples are reassigned across evaluation shards.",
                    "The small online canary is roughly flat; its confidence interval still overlaps a modest decline.",
                ),
            ),
            LatentQuestionRendering(
                rendering_id="alternate",
                instruction="Work out what is going on and make whatever progress you think is most useful.",
                headline="A refreshed retrieval encoder looks worse offline even though the training run appears normal.",
                artifacts=(
                    "Compared with the previous encoder, NDCG@10 falls by about 7% and recall@50 by about 5.5%.",
                    "The refreshed embedding space shows a centroid displacement near 0.10 cosine and about 18% neighbor turnover.",
                    "No clear failure appears in the loss curve, sampler composition, or optimizer telemetry.",
                    "One evaluation shard carries a much larger regression than the rest despite a broadly similar query-domain mix.",
                    "A fixed 2,000-query replay preserves raw candidate scores, yet moving those same examples across evaluation shards shifts aggregate NDCG by roughly 1.2 points.",
                    "The online canary is close to flat, although the sample is not yet large enough to rule out a small decline.",
                ),
            ),
        ),
    ),
}


class LatentQuestionWorld:
    """Counterfactual retrieval worlds for testing whether a quiet anomaly becomes a question.

    The world exposes a salient representation-drift story in both cases. A weaker
    evaluation-path clue is either incidental (R) or decision-relevant (E). The
    mechanical model is only a fixture; human validation must determine whether the
    visible evidence supports the intended distinction without making it obvious.
    """

    causes = CAUSES
    observations = OBSERVATIONS

    def __init__(self, world_id: str, budget: int = 7):
        if world_id not in PAIR_CONTEXTS:
            raise ValueError(f"unknown latent-question world: {world_id}")
        self.context = PAIR_CONTEXTS[world_id]
        self.budget = budget
        self.actions: Dict[str, ActionSpec] = {
            "embedding_stability_probe": ActionSpec(
                "embedding_stability_probe",
                2,
                {
                    "representation_drift": 0.90,
                    "evaluation_path_artifact": 0.18,
                    "corpus_shift": 0.45,
                    "serving_mismatch": 0.25,
                },
                "Probe representation stability with matched queries and neighborhood comparisons.",
            ),
            "route_conditioned_replay": ActionSpec(
                "route_conditioned_replay",
                2,
                {
                    "representation_drift": 0.16,
                    "evaluation_path_artifact": 0.92,
                    "corpus_shift": 0.18,
                    "serving_mismatch": 0.25,
                },
                "Replay the same examples while varying only the evaluation path or shard assignment.",
            ),
            "corpus_slice_audit": ActionSpec(
                "corpus_slice_audit",
                2,
                {
                    "representation_drift": 0.25,
                    "evaluation_path_artifact": 0.20,
                    "corpus_shift": 0.90,
                    "serving_mismatch": 0.20,
                },
                "Audit corpus composition and query slices for distribution change.",
            ),
            "online_offline_compare": ActionSpec(
                "online_offline_compare",
                3,
                {
                    "representation_drift": 0.30,
                    "evaluation_path_artifact": 0.35,
                    "corpus_shift": 0.25,
                    "serving_mismatch": 0.90,
                },
                "Compare matched online and offline behavior under the same requests.",
            ),
            "dashboard_deepdive": ActionSpec(
                "dashboard_deepdive",
                1,
                {
                    "representation_drift": 0.42,
                    "evaluation_path_artifact": 0.40,
                    "corpus_shift": 0.38,
                    "serving_mismatch": 0.41,
                },
                "Inspect more dashboard slices without changing the experimental setup.",
            ),
            "full_reembed": ActionSpec(
                "full_reembed",
                6,
                {
                    "representation_drift": 0.72,
                    "evaluation_path_artifact": 0.30,
                    "corpus_shift": 0.55,
                    "serving_mismatch": 0.38,
                },
                "Re-embed the corpus and rerun the full offline pipeline.",
            ),
        }
        self.terminal_actions = (
            "repair_representation",
            "repair_evaluation_path",
            "refresh_corpus",
            "repair_serving",
            "defer",
        )
        self.reward_matrix = {
            "repair_representation": {
                "representation_drift": 12,
                "evaluation_path_artifact": -6,
                "corpus_shift": -6,
                "serving_mismatch": -6,
            },
            "repair_evaluation_path": {
                "representation_drift": -6,
                "evaluation_path_artifact": 12,
                "corpus_shift": -6,
                "serving_mismatch": -6,
            },
            "refresh_corpus": {
                "representation_drift": -6,
                "evaluation_path_artifact": -6,
                "corpus_shift": 12,
                "serving_mismatch": -6,
            },
            "repair_serving": {
                "representation_drift": -6,
                "evaluation_path_artifact": -6,
                "corpus_shift": -6,
                "serving_mismatch": 12,
            },
            "defer": {c: -1 for c in self.causes},
        }

    @property
    def initial_posterior(self) -> Dict[str, float]:
        return dict(self.context.initial_posterior)

    def rendering(self, rendering_id: str) -> LatentQuestionRendering:
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
    "LatentQuestionContext",
    "LatentQuestionRendering",
    "LatentQuestionWorld",
]
