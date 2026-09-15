from paj_eval.feature_freshness import FeatureFreshnessWorld
from paj_eval.oracle import OraclePlanner


def _first_decision(world):
    planner = OraclePlanner(world)
    return planner, planner.best_decision(
        world.initial_posterior,
        world.budget,
        set(world.actions),
    )


def test_feature_freshness_pair_flips_first_investigation():
    world_c = FeatureFreshnessWorld("C")
    world_f = FeatureFreshnessWorld("F")

    _, (_, decision_c) = _first_decision(world_c)
    _, (_, decision_f) = _first_decision(world_f)

    assert decision_c == ("investigate", "calibration_replay")
    assert decision_f == ("investigate", "feature_freshness_probe")


def test_opposite_world_first_move_has_nontrivial_regret():
    world_c = FeatureFreshnessWorld("C")
    world_f = FeatureFreshnessWorld("F")

    planner_c, (value_c, _) = _first_decision(world_c)
    planner_f, (value_f, _) = _first_decision(world_f)

    forced_freshness_c = planner_c.forced_action_value(
        world_c.initial_posterior,
        world_c.budget,
        set(world_c.actions),
        "feature_freshness_probe",
    )
    forced_calibration_f = planner_f.forced_action_value(
        world_f.initial_posterior,
        world_f.budget,
        set(world_f.actions),
        "calibration_replay",
    )

    assert value_c - forced_freshness_c > 1.0
    assert value_f - forced_calibration_f > 1.0


def test_feature_pair_holds_semantics_fixed():
    world_c = FeatureFreshnessWorld("C")
    world_f = FeatureFreshnessWorld("F")

    assert world_c.budget == world_f.budget
    assert world_c.actions == world_f.actions
    assert world_c.reward_matrix == world_f.reward_matrix
    assert world_c.terminal_actions == world_f.terminal_actions


def test_feature_surface_prompt_is_open_ended_and_does_not_name_action_ids():
    forbidden = {
        "model_calibration_drift",
        "stale_online_features",
        "calibration_replay",
        "feature_freshness_probe",
        "recalibrate_model",
        "repair_materialization",
    }

    for world_id in ("C", "F"):
        world = FeatureFreshnessWorld(world_id)
        for rendering in world.context.renderings:
            visible = " ".join(
                (rendering.instruction, rendering.headline, *rendering.artifacts)
            ).lower()
            for token in forbidden:
                assert token.lower() not in visible
            instruction = rendering.instruction.lower()
            assert "which" not in instruction
            assert "choose" not in instruction
            assert "diagnose" not in instruction
            assert "root cause" not in instruction
