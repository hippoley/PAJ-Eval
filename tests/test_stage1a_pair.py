from paj_eval.oracle import OraclePlanner
from paj_eval.stage1a import Stage1ACounterfactualWorld
from paj_eval.world import OBSERVATIONS


def _forced_first_value(world, posterior, action_name):
    planner = OraclePlanner(world)
    spec = world.actions[action_name]
    unused = set(world.actions)
    unused.remove(action_name)

    value = -float(spec.cost)
    for observation in OBSERVATIONS:
        p_obs = world.observation_prob(posterior, action_name, observation)
        if p_obs <= 0:
            continue
        posterior_next = world.update_posterior(posterior, action_name, observation)
        continuation, _ = planner.best_decision(
            posterior_next,
            world.budget - spec.cost,
            unused,
        )
        value += p_obs * continuation
    return value


def test_pair_has_same_headline_anomaly_across_worlds():
    a = Stage1ACounterfactualWorld("A")
    b = Stage1ACounterfactualWorld("B")

    assert a.rendering("classification").headline == b.rendering("classification").headline
    assert a.rendering("retrieval").headline == b.rendering("retrieval").headline


def test_oracle_first_action_flips_across_counterfactual_pair():
    a = Stage1ACounterfactualWorld("A")
    b = Stage1ACounterfactualWorld("B")

    _, decision_a = OraclePlanner(a).best_decision(
        a.initial_posterior, a.budget, set(a.actions)
    )
    _, decision_b = OraclePlanner(b).best_decision(
        b.initial_posterior, b.budget, set(b.actions)
    )

    assert decision_a == ("investigate", "rerun_seeds")
    assert decision_b == ("investigate", "recompute_metrics")


def test_copying_other_world_first_move_has_material_regret():
    a = Stage1ACounterfactualWorld("A")
    b = Stage1ACounterfactualWorld("B")

    planner_a = OraclePlanner(a)
    value_a, _ = planner_a.best_decision(a.initial_posterior, a.budget, set(a.actions))
    wrong_a = _forced_first_value(a, a.initial_posterior, "recompute_metrics")

    planner_b = OraclePlanner(b)
    value_b, _ = planner_b.best_decision(b.initial_posterior, b.budget, set(b.actions))
    wrong_b = _forced_first_value(b, b.initial_posterior, "rerun_seeds")

    assert value_a - wrong_a > 1.0
    assert value_b - wrong_b > 1.0


def test_surface_rendering_does_not_change_normative_world_state():
    for world_id in ("A", "B"):
        world = Stage1ACounterfactualWorld(world_id)
        before = dict(world.initial_posterior)
        _ = world.rendering("classification")
        _ = world.rendering("retrieval")
        assert world.initial_posterior == before
