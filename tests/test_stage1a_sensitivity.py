from paj_eval.oracle import OraclePlanner
from paj_eval.stage1a import Stage1ACounterfactualWorld
from paj_eval.world import ActionSpec


def _decision(world, posterior):
    return OraclePlanner(world).best_decision(
        posterior, world.budget, set(world.actions)
    )[1]


def test_counterfactual_flip_is_robust_to_moderate_posterior_perturbation():
    # Hold preprocessing + capacity at 0.25 total and move 0.75 probability
    # mass between evaluation and optimization. A/B should remain on opposite
    # sides of the action boundary under +/- 0.10 perturbations.
    a = Stage1ACounterfactualWorld("A")
    b = Stage1ACounterfactualWorld("B")

    for opt in (0.45, 0.50, 0.55, 0.60, 0.65):
        posterior = {
            "preprocessing": 0.15,
            "evaluation": 0.75 - opt,
            "optimization": opt,
            "capacity": 0.10,
        }
        assert _decision(a, posterior) == ("investigate", "rerun_seeds")

    for opt in (0.10, 0.15, 0.20, 0.25, 0.30):
        posterior = {
            "preprocessing": 0.15,
            "evaluation": 0.75 - opt,
            "optimization": opt,
            "capacity": 0.10,
        }
        assert _decision(b, posterior) == ("investigate", "recompute_metrics")


def test_counterfactual_flip_survives_cost_perturbations():
    for world_id, expected in (
        ("A", ("investigate", "rerun_seeds")),
        ("B", ("investigate", "recompute_metrics")),
    ):
        for rerun_cost in (1, 2, 3):
            for recompute_cost in (1, 2, 3):
                world = Stage1ACounterfactualWorld(world_id)
                rerun = world.actions["rerun_seeds"]
                recompute = world.actions["recompute_metrics"]
                world.actions["rerun_seeds"] = ActionSpec(
                    rerun.name, rerun_cost, rerun.signal_prob, rerun.description
                )
                world.actions["recompute_metrics"] = ActionSpec(
                    recompute.name,
                    recompute_cost,
                    recompute.signal_prob,
                    recompute.description,
                )
                assert _decision(world, world.initial_posterior) == expected
