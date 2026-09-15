from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
import math, random

CAUSES = ("preprocessing", "evaluation", "optimization", "capacity")
OBSERVATIONS = ("signal", "no_signal")
INITIAL_CLUES = ("slice_anomaly", "metric_inconsistency", "seed_variance", "underfit_pattern", "ambiguous")

@dataclass(frozen=True)
class ActionSpec:
    name: str
    cost: int
    signal_prob: Dict[str, float]
    description: str

@dataclass
class StepRecord:
    action: str
    cost: int
    observation: str
    posterior_before: Dict[str, float]
    posterior_after: Dict[str, float]
    eig: float
    eig_per_cost: float
    remaining_budget: int

@dataclass
class EpisodeTrace:
    true_cause: str
    initial_clue: str
    initial_posterior: Dict[str, float]
    initial_budget: int
    steps: List[StepRecord]
    terminal_action: str
    terminal_expected_reward: float
    realized_terminal_reward: float
    total_cost: int
    research_utility_expected: float
    research_utility_realized: float
    total_eig: float
    information_acquisition_efficiency: float
    def to_dict(self):
        return {
            "true_cause": self.true_cause,
            "initial_clue": self.initial_clue,
            "initial_posterior": self.initial_posterior,
            "initial_budget": self.initial_budget,
            "steps": [{**asdict(s)} for s in self.steps],
            "terminal_action": self.terminal_action,
            "terminal_expected_reward": self.terminal_expected_reward,
            "realized_terminal_reward": self.realized_terminal_reward,
            "total_cost": self.total_cost,
            "research_utility_expected": self.research_utility_expected,
            "research_utility_realized": self.research_utility_realized,
            "total_eig": self.total_eig,
            "information_acquisition_efficiency": self.information_acquisition_efficiency,
        }

def entropy(posterior: Dict[str, float]) -> float:
    h = 0.0
    for p in posterior.values():
        if p > 0:
            h -= p * math.log2(p)
    return h

class ToyResearchWorld:
    def __init__(self, budget: int = 8, rng: Optional[random.Random] = None):
        self.budget = budget
        self.rng = rng or random.Random()
        self.prior = {c: 1.0 / len(CAUSES) for c in CAUSES}
        self.actions: Dict[str, ActionSpec] = {
            "subgroup_metrics": ActionSpec("subgroup_metrics", 1,
                {"preprocessing":0.78,"evaluation":0.20,"optimization":0.18,"capacity":0.22},
                "Break core metrics down across hidden data subgroups."),
            "preprocess_audit": ActionSpec("preprocess_audit", 2,
                {"preprocessing":0.93,"evaluation":0.10,"optimization":0.10,"capacity":0.12},
                "Inspect transformed examples and preprocessing outputs."),
            "recompute_metrics": ActionSpec("recompute_metrics", 2,
                {"preprocessing":0.12,"evaluation":0.92,"optimization":0.12,"capacity":0.12},
                "Recompute evaluation metrics from raw predictions."),
            "rerun_seeds": ActionSpec("rerun_seeds", 3,
                {"preprocessing":0.18,"evaluation":0.16,"optimization":0.90,"capacity":0.22},
                "Repeat training across multiple random seeds."),
            "capacity_sweep": ActionSpec("capacity_sweep", 4,
                {"preprocessing":0.14,"evaluation":0.12,"optimization":0.20,"capacity":0.88},
                "Train a small capacity sweep and compare systematic underfit."),
            "raw_sample_audit": ActionSpec("raw_sample_audit", 2,
                {"preprocessing":0.60,"evaluation":0.34,"optimization":0.22,"capacity":0.16},
                "Inspect targeted raw examples and prediction errors."),
            "full_retrain": ActionSpec("full_retrain", 7,
                {"preprocessing":0.58,"evaluation":0.46,"optimization":0.64,"capacity":0.68},
                "Run an expensive full retraining experiment with several changes."),
        }

        self.initial_clue_prob = {
            "preprocessing": {"slice_anomaly":0.50,"metric_inconsistency":0.15,"seed_variance":0.15,"underfit_pattern":0.15,"ambiguous":0.05},
            "evaluation": {"slice_anomaly":0.15,"metric_inconsistency":0.50,"seed_variance":0.15,"underfit_pattern":0.15,"ambiguous":0.05},
            "optimization": {"slice_anomaly":0.15,"metric_inconsistency":0.15,"seed_variance":0.50,"underfit_pattern":0.15,"ambiguous":0.05},
            "capacity": {"slice_anomaly":0.15,"metric_inconsistency":0.15,"seed_variance":0.15,"underfit_pattern":0.50,"ambiguous":0.05},
        }
        self.terminal_actions = (
            "fix_preprocessing","fix_evaluation","fix_optimization","increase_capacity","defer"
        )
        self.reward_matrix = {
            "fix_preprocessing": {"preprocessing":12,"evaluation":-6,"optimization":-6,"capacity":-6},
            "fix_evaluation": {"preprocessing":-6,"evaluation":12,"optimization":-6,"capacity":-6},
            "fix_optimization": {"preprocessing":-6,"evaluation":-6,"optimization":12,"capacity":-6},
            "increase_capacity": {"preprocessing":-6,"evaluation":-6,"optimization":-6,"capacity":12},
            "defer": {c:-1 for c in CAUSES},
        }
    def sample_cause(self) -> str:
        return self.rng.choice(CAUSES)

    def sample_initial_clue(self, true_cause: str) -> str:
        r = self.rng.random()
        acc = 0.0
        for clue in INITIAL_CLUES:
            acc += self.initial_clue_prob[true_cause][clue]
            if r <= acc:
                return clue
        return INITIAL_CLUES[-1]
    def posterior_from_initial_clue(self, clue: str):
        weights = {c:self.prior[c]*self.initial_clue_prob[c][clue] for c in CAUSES}
        z=sum(weights.values())
        return {c:weights[c]/z for c in CAUSES}
    def likelihood(self, action_name: str, observation: str, cause: str) -> float:
        p = self.actions[action_name].signal_prob[cause]
        return p if observation == "signal" else 1-p
    def observation_prob(self, posterior, action_name, observation):
        return sum(posterior[c]*self.likelihood(action_name,observation,c) for c in CAUSES)
    def update_posterior(self, posterior, action_name, observation):
        w = {c:posterior[c]*self.likelihood(action_name,observation,c) for c in CAUSES}
        z = sum(w.values())
        return {c:w[c]/z for c in CAUSES} if z else dict(posterior)
    def sample_observation(self, true_cause, action_name):
        p = self.actions[action_name].signal_prob[true_cause]
        return "signal" if self.rng.random() < p else "no_signal"
    def eig(self, posterior, action_name):
        h0 = entropy(posterior)
        eh = 0.0
        for obs in OBSERVATIONS:
            po = self.observation_prob(posterior,action_name,obs)
            if po > 0:
                eh += po * entropy(self.update_posterior(posterior,action_name,obs))
        return h0-eh
    def best_terminal_action(self, posterior) -> Tuple[str,float]:
        best_a, best_v = None, -1e18
        for a in self.terminal_actions:
            v = sum(posterior[c]*self.reward_matrix[a][c] for c in CAUSES)
            if v > best_v:
                best_a, best_v = a, v
        return best_a, best_v
    def run_policy(self, policy, true_cause=None):
        cause = true_cause or self.sample_cause()
        initial_clue = self.sample_initial_clue(cause)
        posterior = self.posterior_from_initial_clue(initial_clue)
        initial_posterior = dict(posterior)
        remaining = self.budget
        unused = set(self.actions)
        steps=[]; total_cost=0; total_eig=0.0
        while True:
            decision = policy.choose(self, posterior, remaining, unused)
            if decision[0] == "stop":
                terminal_action = decision[1]
                break
            action_name = decision[1]
            spec = self.actions[action_name]
            if action_name not in unused or spec.cost > remaining:
                raise ValueError("invalid action")
            eig = self.eig(posterior, action_name)
            obs = self.sample_observation(cause, action_name)
            before = dict(posterior)
            posterior = self.update_posterior(posterior, action_name, obs)
            remaining -= spec.cost; total_cost += spec.cost; total_eig += eig
            unused.remove(action_name)
            steps.append(StepRecord(action_name,spec.cost,obs,before,dict(posterior),eig,eig/spec.cost,remaining))
            if not any(self.actions[a].cost <= remaining for a in unused):
                terminal_action,_ = self.best_terminal_action(posterior)
                break
        terminal_expected = sum(posterior[c]*self.reward_matrix[terminal_action][c] for c in CAUSES)
        terminal_realized = self.reward_matrix[terminal_action][cause]
        return EpisodeTrace(cause,initial_clue,initial_posterior,self.budget,steps,terminal_action,terminal_expected,terminal_realized,total_cost,
            terminal_expected-total_cost, terminal_realized-total_cost,total_eig,total_eig/total_cost if total_cost else 0.0)
