from paj_eval.latent_question import LatentQuestionWorld
from paj_eval.oracle import OraclePlanner


def _first_decision(world):
    planner = OraclePlanner(world)
    return planner, planner.best_decision(
        world.initial_posterior,
        world.budget,
        set(world.actions),
    )


def test_latent_question_pair_flips_first_investigation():
    world_r = LatentQuestionWorld("R")
    world_s = LatentQuestionWorld("S")

    _, (_, decision_r) = _first_decision(world_r)
    _, (_, decision_s) = _first_decision(world_s)

    assert decision_r == ("investigate", "embedding_stability_probe")
    assert decision_s == ("investigate", "index_freshness_probe")


def test_opposite_world_first_move_has_nontrivial_regret():
    world_r = LatentQuestionWorld("R")
    world_s = LatentQuestionWorld("S")

    planner_r, (value_r, _) = _first_decision(world_r)
    planner_s, (value_s, _) = _first_decision(world_s)

    forced_index_r = planner_r.forced_action_value(
        world_r.initial_posterior,
        world_r.budget,
        set(world_r.actions),
        "index_freshness_probe",
    )
    forced_embedding_s = planner_s.forced_action_value(
        world_s.initial_posterior,
        world_s.budget,
        set(world_s.actions),
        "embedding_stability_probe",
    )

    assert value_r - forced_index_r > 1.0
    assert value_s - forced_embedding_s > 1.0


def test_pair_holds_intervention_semantics_fixed():
    world_r = LatentQuestionWorld("R")
    world_s = LatentQuestionWorld("S")

    assert world_r.budget == world_s.budget
    assert world_r.actions == world_s.actions
    assert world_r.reward_matrix == world_s.reward_matrix
    assert world_r.terminal_actions == world_s.terminal_actions


def test_surface_prompt_does_not_name_hidden_state_or_action_ids():
    forbidden = {
        "representation_drift",
        "stale_index",
        "embedding_stability_probe",
        "index_freshness_probe",
        "repair_representation",
        "rebuild_index",
    }

    for world_id in ("R", "S"):
        world = LatentQuestionWorld(world_id)
        for rendering in world.context.renderings:
            visible = " ".join(
                (rendering.instruction, rendering.headline, *rendering.artifacts)
            ).lower()
            for token in forbidden:
                assert token.lower() not in visible


def test_surface_renderings_keep_task_open_ended():
    for world_id in ("R", "S"):
        world = LatentQuestionWorld(world_id)
        assert len(world.context.renderings) == 2
        for rendering in world.context.renderings:
            instruction = rendering.instruction.lower()
            assert "which" not in instruction
            assert "choose" not in instruction
            assert "diagnose" not in instruction
            assert "root cause" not in instruction
