from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .world import ActionSpec, ToyResearchWorld


@dataclass(frozen=True)
class SurfaceRendering:
    rendering_id: str
    headline: str
    artifacts: Tuple[str, ...]


@dataclass(frozen=True)
class PairContext:
    world_id: str
    latent_story: str
    initial_posterior: Dict[str, float]
    renderings: Tuple[SurfaceRendering, ...]


# Stage 1A is deliberately small. Both worlds share the same high-level anomaly
# (seed-to-seed disagreement after a stack update), but weak contextual evidence
# changes which diagnostic should be purchased first. The latent posterior here is
# an explicit test fixture, not a final claim that these numbers are calibrated to
# real ML systems. Expert walkthroughs are intended to attack that assumption.
PAIR_CONTEXTS: Dict[str, PairContext] = {
    "A": PairContext(
        world_id="A",
        latent_story="optimization instability is the leading causal family",
        initial_posterior={
            "preprocessing": 0.15,
            "evaluation": 0.20,
            "optimization": 0.55,
            "capacity": 0.10,
        },
        renderings=(
            SurfaceRendering(
                rendering_id="classification",
                headline="Validation quality fell after a training-stack update; five reruns now disagree.",
                artifacts=(
                    "Training loss remains smooth, but validation F1 varies by roughly two points across seeds.",
                    "Two reruns emit optimizer-state restoration warnings after the dependency update.",
                    "Cached raw prediction arrays differ across reruns, not only the displayed aggregate metric.",
                    "The evaluation script checksum matches the previous release.",
                    "No stable subgroup accounts for the full regression.",
                ),
            ),
            SurfaceRendering(
                rendering_id="retrieval",
                headline="Offline ranking quality fell after a training-stack update; five reruns now disagree.",
                artifacts=(
                    "Training objectives remain smooth, but NDCG varies materially across random seeds.",
                    "Two reruns emit optimizer-state restoration warnings after the dependency update.",
                    "Cached query-document scores differ across reruns, not only the dashboard aggregate.",
                    "The evaluation script checksum matches the previous release.",
                    "No stable query segment accounts for the full regression.",
                ),
            ),
        ),
    ),
    "B": PairContext(
        world_id="B",
        latent_story="an evaluation artifact is the leading causal family",
        initial_posterior={
            "preprocessing": 0.15,
            "evaluation": 0.55,
            "optimization": 0.20,
            "capacity": 0.10,
        },
        renderings=(
            SurfaceRendering(
                rendering_id="classification",
                headline="Validation quality fell after a training-stack update; five reruns now disagree.",
                artifacts=(
                    "Training loss remains smooth, while displayed validation F1 varies by roughly two points across seeds.",
                    "Optimizer defaults and restored state hashes match the previous release.",
                    "Cached raw prediction arrays are effectively identical where dashboard metrics disagree.",
                    "The metric aggregation dependency changed in the same stack update.",
                    "No stable subgroup accounts for the full regression.",
                ),
            ),
            SurfaceRendering(
                rendering_id="retrieval",
                headline="Offline ranking quality fell after a training-stack update; five reruns now disagree.",
                artifacts=(
                    "Training objectives remain smooth, while displayed NDCG varies materially across seeds.",
                    "Optimizer defaults and restored state hashes match the previous release.",
                    "Cached query-document scores are effectively identical where dashboard metrics disagree.",
                    "The metric aggregation dependency changed in the same stack update.",
                    "No stable query segment accounts for the full regression.",
                ),
            ),
        ),
    ),
}


class Stage1ACounterfactualWorld(ToyResearchWorld):
    """A small adversarial pair for testing counterfactual sensitivity.

    The action semantics and likelihood model are held fixed across A and B.
    Only the initial evidence state changes. This is intentional: the pair asks
    whether a similar headline anomaly can imply a different best next action
    after weak contextual evidence is integrated.
    """

    def __init__(self, world_id: str, budget: int = 8):
        if world_id not in PAIR_CONTEXTS:
            raise ValueError(f"unknown Stage 1A world: {world_id}")
        super().__init__(budget=budget)
        self.context = PAIR_CONTEXTS[world_id]

        # Remove the universal attraction of the original cheap subgroup probe.
        # These likelihoods are shared by both counterfactual worlds.
        self.actions = {
            "subgroup_metrics": ActionSpec(
                "subgroup_metrics", 1,
                {"preprocessing": 0.48, "evaluation": 0.40, "optimization": 0.36, "capacity": 0.42},
                "Break core metrics down across hidden data subgroups.",
            ),
            "preprocess_audit": ActionSpec(
                "preprocess_audit", 2,
                {"preprocessing": 0.92, "evaluation": 0.12, "optimization": 0.12, "capacity": 0.15},
                "Inspect transformed examples and preprocessing outputs.",
            ),
            "recompute_metrics": ActionSpec(
                "recompute_metrics", 2,
                {"preprocessing": 0.12, "evaluation": 0.94, "optimization": 0.14, "capacity": 0.12},
                "Recompute evaluation metrics from raw predictions or scores.",
            ),
            "rerun_seeds": ActionSpec(
                "rerun_seeds", 2,
                {"preprocessing": 0.14, "evaluation": 0.14, "optimization": 0.96, "capacity": 0.18},
                "Repeat the training or fitting procedure across controlled random seeds.",
            ),
            "capacity_sweep": ActionSpec(
                "capacity_sweep", 4,
                {"preprocessing": 0.14, "evaluation": 0.12, "optimization": 0.18, "capacity": 0.90},
                "Run a small capacity sweep and compare systematic underfit.",
            ),
            "raw_sample_audit": ActionSpec(
                "raw_sample_audit", 2,
                {"preprocessing": 0.66, "evaluation": 0.32, "optimization": 0.24, "capacity": 0.18},
                "Inspect targeted raw examples and prediction or score errors.",
            ),
            "full_retrain": ActionSpec(
                "full_retrain", 7,
                {"preprocessing": 0.58, "evaluation": 0.46, "optimization": 0.64, "capacity": 0.68},
                "Run an expensive full retraining experiment with several changes.",
            ),
        }

    @property
    def initial_posterior(self) -> Dict[str, float]:
        return dict(self.context.initial_posterior)

    def rendering(self, rendering_id: str) -> SurfaceRendering:
        for rendering in self.context.renderings:
            if rendering.rendering_id == rendering_id:
                return rendering
        raise ValueError(f"unknown rendering {rendering_id!r} for world {self.context.world_id}")


__all__ = [
    "PAIR_CONTEXTS",
    "PairContext",
    "SurfaceRendering",
    "Stage1ACounterfactualWorld",
]
