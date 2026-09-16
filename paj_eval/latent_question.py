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
    "stale_index",
    "corpus_shift",
    "serving_mismatch",
)
OBSERVATIONS = ("signal", "no_signal")


PAIR_CONTEXTS: Dict[str, LatentQuestionContext] = {
    "R": LatentQuestionContext(
        world_id="R",
        initial_posterior={
            "representation_drift": 0.50,
            "stale_index": 0.15,
            "corpus_shift": 0.22,
            "serving_mismatch": 0.13,
        },
        renderings=(
            LatentQuestionRendering(
                rendering_id="primary",
                instruction="You have inherited this system after a routine release. Decide what you would do next.",
                headline="Retrieval quality is worse after a scheduled model-and-corpus refresh; the release pipeline is green.",
                artifacts=(
                    "NDCG@10 is down 7.0% and recall@50 is down 5.6% relative to the previous release.",
                    "Query-embedding centroids moved by about 0.11 cosine distance and nearest-neighbor turnover increased to 19%.",
                    "Training loss, negative-sampling mix, and optimizer telemetry look similar to recent successful runs.",
                    "The corpus refresh completed with the expected document count and the indexing stage completed within its usual runtime band.",
                    "A routine post-release sample of document identifiers resolves to the current corpus snapshot.",
                    "A small online canary trends downward too, although its confidence interval is still wide.",
                ),
            ),
            LatentQuestionRendering(
                rendering_id="alternate",
                instruction="You are taking over this system after a routine release. What would you do next?",
                headline="Retrieval metrics worsened after the latest model-and-corpus refresh even though the release completed normally.",
                artifacts=(
                    "Relative to the previous release, NDCG@10 falls about 7% and recall@50 about 5.5%.",
                    "The query embedding space shifts by roughly 0.11 cosine at the centroid level, with about one-fifth neighbor turnover.",
                    "Loss curves, sampler composition, and optimizer telemetry resemble recent healthy runs.",
                    "The corpus job produced the expected document count and the indexing stage finished in its normal time range.",
                    "A routine sample of document IDs after release points to the current corpus snapshot.",
                    "The online canary points in the same direction as the offline regression, but remains underpowered.",
                ),
            ),
        ),
    ),
    "S": LatentQuestionContext(
        world_id="S",
        initial_posterior={
            "representation_drift": 0.28,
            "stale_index": 0.46,
            "corpus_shift": 0.16,
            "serving_mismatch": 0.10,
        },
        renderings=(
            LatentQuestionRendering(
                rendering_id="primary",
                instruction="You have inherited this system after a routine release. Decide what you would do next.",
                headline="Retrieval quality is worse after a scheduled model-and-corpus refresh; the release pipeline is green.",
                artifacts=(
                    "NDCG@10 is down 7.1% and recall@50 is down 5.4% relative to the previous release.",
                    "Query-embedding centroids moved by about 0.10 cosine distance and nearest-neighbor turnover increased to 18%.",
                    "Training loss, negative-sampling mix, and optimizer telemetry look similar to recent successful runs.",
                    "The corpus refresh completed with the expected document count; storage usage for the retrieval artifacts is almost unchanged from the previous release.",
                    "A routine post-release sample of document identifiers resolves successfully, but the sample does not record which index generation served each lookup.",
                    "The small online canary is roughly flat; its confidence interval still overlaps a modest decline.",
                ),
            ),
            LatentQuestionRendering(
                rendering_id="alternate",
                instruction="You are taking over this system after a routine release. What would you do next?",
                headline="Retrieval metrics worsened after the latest model-and-corpus refresh even though the release completed normally.",
                artifacts=(
                    "Relative to the previous release, NDCG@10 falls about 7% and recall@50 about 5.5%.",
                    "The query embedding space shifts by roughly 0.10 cosine at the centroid level, with around 18% neighbor turnover.",
                    "Loss curves, sampler composition, and optimizer telemetry resemble recent healthy runs.",
                    "The corpus job reports the expected document count, while disk usage for retrieval artifacts is nearly identical to the prior release.",
                    "Routine document-ID lookups succeed after release, although the check does not preserve the serving index-generation identifier.",
                    "The online canary is close to flat, although the sample is not yet large enough to exclude a small decline.",
                ),
            ),
        ),
    ),
}


class LatentQuestionWorld:
    """Retrieval worlds for testing whether a quiet infrastructure anomaly becomes a question.

    Both worlds support a salient representation-drift story after an embedding-model
    refresh. In R the index was actually rebuilt and representation drift remains the
    leading family. In S a quieter freshness anomaly makes a stale index more plausible.
    The mechanical posterior is a fixture, not human-validity evidence.
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
                "embedding_stability_probe", 2,
                {"representation_drift": 0.90, "stale_index": 0.45, "corpus_shift": 0.45, "serving_mismatch": 0.25},
                "Compare matched queries under old and new embeddings against a fresh brute-force reference.",
            ),
            "index_freshness_probe": ActionSpec(
                "index_freshness_probe", 2,
                {"representation_drift": 0.25, "stale_index": 0.90, "corpus_shift": 0.25, "serving_mismatch": 0.25},
                "Check index generation/freshness and compare indexed vectors with the current source corpus.",
            ),
            "corpus_slice_audit": ActionSpec(
                "corpus_slice_audit", 2,
                {"representation_drift": 0.25, "stale_index": 0.20, "corpus_shift": 0.90, "serving_mismatch": 0.20},
                "Audit corpus composition and query slices for distribution change.",
            ),
            "online_offline_compare": ActionSpec(
                "online_offline_compare", 3,
                {"representation_drift": 0.35, "stale_index": 0.45, "corpus_shift": 0.25, "serving_mismatch": 0.90},
                "Compare matched online and offline behavior under the same requests.",
            ),
            "dashboard_deepdive": ActionSpec(
                "dashboard_deepdive", 1,
                {"representation_drift": 0.42, "stale_index": 0.40, "corpus_shift": 0.38, "serving_mismatch": 0.41},
                "Inspect more existing dashboard slices without changing the experimental setup.",
            ),
            "full_reindex": ActionSpec(
                "full_reindex", 5,
                {"representation_drift": 0.45, "stale_index": 0.85, "corpus_shift": 0.42, "serving_mismatch": 0.35},
                "Force a full corpus re-embedding and vector-index rebuild.",
            ),
        }
        self.terminal_actions = ("repair_representation", "rebuild_index", "refresh_corpus", "repair_serving", "defer")
        self.reward_matrix = {
            "repair_representation": {"representation_drift": 12, "stale_index": -6, "corpus_shift": -6, "serving_mismatch": -6},
            "rebuild_index": {"representation_drift": -6, "stale_index": 12, "corpus_shift": -6, "serving_mismatch": -6},
            "refresh_corpus": {"representation_drift": -6, "stale_index": -6, "corpus_shift": 12, "serving_mismatch": -6},
            "repair_serving": {"representation_drift": -6, "stale_index": -6, "corpus_shift": -6, "serving_mismatch": 12},
            "defer": {c: -1 for c in self.causes},
        }

    @property
    def initial_posterior(self) -> Dict[str, float]:
        return dict(self.context.initial_posterior)

    def rendering(self, rendering_id: str) -> LatentQuestionRendering:
        for rendering in self.context.renderings:
            if rendering.rendering_id == rendering_id:
                return rendering
        raise ValueError(f"unknown rendering {rendering_id!r} for world {self.context.world_id}")

    def likelihood(self, action_name: str, observation: str, cause: str) -> float:
        p = self.actions[action_name].signal_prob[cause]
        return p if observation == "signal" else 1.0 - p

    def observation_prob(self, posterior, action_name, observation):
        return sum(posterior[c] * self.likelihood(action_name, observation, c) for c in self.causes)

    def update_posterior(self, posterior, action_name, observation):
        weights = {c: posterior[c] * self.likelihood(action_name, observation, c) for c in self.causes}
        z = sum(weights.values())
        return {c: weights[c] / z for c in self.causes} if z else dict(posterior)

    def eig(self, posterior, action_name):
        h0 = entropy(posterior)
        expected_h = 0.0
        for observation in self.observations:
            po = self.observation_prob(posterior, action_name, observation)
            if po > 0:
                expected_h += po * entropy(self.update_posterior(posterior, action_name, observation))
        return h0 - expected_h

    def best_terminal_action(self, posterior):
        best_action, best_value = None, -1e18
        for action in self.terminal_actions:
            value = sum(posterior[c] * self.reward_matrix[action][c] for c in self.causes)
            if value > best_value:
                best_action, best_value = action, value
        return best_action, best_value


__all__ = ["CAUSES", "OBSERVATIONS", "PAIR_CONTEXTS", "LatentQuestionContext", "LatentQuestionRendering", "LatentQuestionWorld"]
