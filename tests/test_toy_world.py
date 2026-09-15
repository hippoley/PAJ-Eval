import random

from paj_eval.world import ToyResearchWorld
from paj_eval.oracle import OraclePlanner
from paj_eval.policies import GreedyEIGPolicy, RandomPolicy


def test_posterior_normalizes():
    w = ToyResearchWorld(rng=random.Random(1))
    p = w.update_posterior(w.prior, "preprocess_audit", "signal")
    assert abs(sum(p.values()) - 1) < 1e-9


def test_eig_nonnegative():
    w = ToyResearchWorld(rng=random.Random(1))
    assert all(w.eig(w.prior, a) >= -1e-10 for a in w.actions)


def test_preprocess_audit_is_diagnostic():
    w = ToyResearchWorld(rng=random.Random(1))
    p = w.update_posterior(w.prior, "preprocess_audit", "signal")
    assert p["preprocessing"] == max(p.values())


def test_oracle_valid():
    w = ToyResearchWorld(rng=random.Random(1))
    planner = OraclePlanner(w)
    v, d = planner.best_decision(w.prior, w.budget, set(w.actions))
    assert d[0] in {"stop", "investigate"}
    assert isinstance(v, float)


def test_oracle_first_action_changes_with_initial_evidence():
    """Stage 0 should not have one universal oracle first move."""
    w = ToyResearchWorld(rng=random.Random(1))
    planner = OraclePlanner(w)
    first_actions = set()
    for clue in ("slice_anomaly", "metric_inconsistency", "seed_variance", "underfit_pattern", "ambiguous"):
        posterior = w.posterior_from_initial_clue(clue)
        _, decision = planner.best_decision(posterior, w.budget, set(w.actions))
        assert decision[0] == "investigate"
        first_actions.add(decision[1])
    assert len(first_actions) >= 3


def test_expected_and_realized_utility_are_separate():
    """Decision quality and realized outcome luck are intentionally distinct outputs."""
    w = ToyResearchWorld(rng=random.Random(11))
    trace = w.run_policy(GreedyEIGPolicy(0.06), true_cause="optimization")
    assert trace.research_utility_expected == trace.terminal_expected_reward - trace.total_cost
    assert trace.research_utility_realized == trace.realized_terminal_reward - trace.total_cost


def test_random_policy_is_reproducible_given_seed():
    def run_once(seed):
        rng = random.Random(seed)
        w = ToyResearchWorld(rng=rng)
        t = w.run_policy(RandomPolicy(rng=rng, stop_prob=0.18))
        return t.to_dict()

    assert run_once(23) == run_once(23)
