from functools import lru_cache
from typing import Dict, Tuple

from .world import CAUSES, OBSERVATIONS


def _belief_key(p: Dict[str, float], causes) -> Tuple[float, ...]:
    return tuple(round(p[c], 10) for c in causes)


def _key_to_belief(k, causes):
    return {c: k[i] for i, c in enumerate(causes)}


class OraclePlanner:
    def __init__(self, world):
        self.world = world
        self.causes = tuple(getattr(world, "causes", CAUSES))
        self.observations = tuple(getattr(world, "observations", OBSERVATIONS))

    @lru_cache(maxsize=None)
    def value(self, belief_key, remaining, unused_frozen):
        p = _key_to_belief(belief_key, self.causes)
        stop_action, stop_value = self.world.best_terminal_action(p)
        best_value, best_decision = stop_value, ("stop", stop_action)
        unused = set(unused_frozen)
        for a in sorted(unused):
            spec = self.world.actions[a]
            if spec.cost > remaining:
                continue
            val = -float(spec.cost)
            future = 0.0
            for obs in self.observations:
                po = self.world.observation_prob(p, a, obs)
                if po <= 0:
                    continue
                post = self.world.update_posterior(p, a, obs)
                nv, _ = self.value(
                    _belief_key(post, self.causes),
                    remaining - spec.cost,
                    frozenset(x for x in unused if x != a),
                )
                future += po * nv
            val += future
            if val > best_value:
                best_value, best_decision = val, ("investigate", a)
        return best_value, best_decision

    def best_decision(self, posterior, remaining, unused):
        return self.value(
            _belief_key(posterior, self.causes), remaining, frozenset(unused)
        )


class OraclePolicy:
    def __init__(self, world):
        self.planner = OraclePlanner(world)

    def choose(self, world, posterior, remaining, unused):
        return self.planner.best_decision(posterior, remaining, unused)[1]
