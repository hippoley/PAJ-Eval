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
    world_e = LatentQuestionWorld("E")

    _, (_, decision_r) = _first_decision(world_r)
    _, (_, decision_e) = _first_decision(world_e)

    assert decision_r == ("investigate", "embedding_stability_probe")
    assert decision_e == ("investigate", "route_conditioned_replay")


def test_opposite_world_first_move_has_nontrivial_regret():
    world_r = LatentQuestionWorld("R")
    world_e = LatentQuestionWorld("E")

    planner_r, (value_r, _) = _first_decision(world_r)
    planner_e, (value_e, _) = _first_decision(world_e)

    forced_route_r = planner_r.forced_action_value(
        world_r.initial_posterior,
        world_r.budget,
        set(world_r.actions),
        "route_conditioned_replay",
    )
    forced_embedding_e = planner_e.forced_action_value(
        world_e.initial_posterior,
        world_e.budget,
        set(world_e.actions),
        "embedding_stability_probe",
    )

    assert value_r - forced_route_r > 0.30
    assert value_e - forced_embedding_e > 0.50


def test_pair_holds_intervention_semantics_fixed():
    world_r = LatentQuestionWorld("R")
    world_e = LatentQuestionWorld("E")

    assert world_r.budget == world_e.budget
    assert world_r.actions == world_e.actions
    assert world_r.reward_matrix == world_e.reward_matrix
    assert world_r.terminal_actions == world_e.terminal_actions


def test_surface_prompt_does_not_name_the_hidden_diagnosis_or_action():
    forbidden = {
        "representation_drift",
        "evaluation_path_artifact",
        "embedding_stability_probe",
        "route_conditioned_replay",
        "repair_representation",
        "repair_evaluation_path",
    }

    for world_id in ("R", "E"):
        world = LatentQuestionWorld(world_id)
        for rendering in world.context.renderings:
            visible = " ".join(
                (rendering.instruction, rendering.headline, *rendering.artifacts)
            ).lower()
            for token in forbidden:
                assert token.lower() not in visible


def test_surface_renderings_keep_task_open_ended():
    for world_id in ("R", "E"):
        world = LatentQuestionWorld(world_id)
        assert len(world.context.renderings) == 2
        for rendering in world.context.renderings:
            instruction = rendering.instruction.lower()
            assert "which" not in instruction
            assert "choose" not in instruction
            assert "diagnose" not in instruction
            assert "root cause" not in instruction
