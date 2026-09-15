import random
from .oracle import OraclePolicy

class GreedyEIGPolicy:
    def __init__(self, threshold=0.06): self.threshold=threshold
    def choose(self, world, posterior, remaining, unused):
        candidates=[]
        for a in unused:
            spec=world.actions[a]
            if spec.cost<=remaining:
                eig=world.eig(posterior,a)
                candidates.append((eig/spec.cost,eig,a))
        terminal,_=world.best_terminal_action(posterior)
        if not candidates: return ("stop",terminal)
        ratio,_,a=max(candidates)
        return ("stop",terminal) if ratio<self.threshold else ("investigate",a)

class ExpensiveBiasPolicy:
    preference=["full_retrain","capacity_sweep","rerun_seeds","raw_sample_audit","recompute_metrics","preprocess_audit","subgroup_metrics"]
    def choose(self, world, posterior, remaining, unused):
        for a in self.preference:
            if a in unused and world.actions[a].cost<=remaining:
                return ("investigate",a)
        terminal,_=world.best_terminal_action(posterior)
        return ("stop",terminal)

class RandomPolicy:
    def __init__(self, rng=None, stop_prob=0.18):
        self.rng=rng or random.Random(); self.stop_prob=stop_prob
    def choose(self, world, posterior, remaining, unused):
        terminal,_=world.best_terminal_action(posterior)
        candidates=[a for a in sorted(unused) if world.actions[a].cost<=remaining]
        if not candidates or self.rng.random()<self.stop_prob:
            return ("stop",terminal)
        return ("investigate",self.rng.choice(candidates))

__all__=["OraclePolicy","GreedyEIGPolicy","ExpensiveBiasPolicy","RandomPolicy"]
