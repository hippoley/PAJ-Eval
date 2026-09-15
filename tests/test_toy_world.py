import random
from paj_eval.world import ToyResearchWorld
from paj_eval.oracle import OraclePlanner

def test_posterior_normalizes():
    w=ToyResearchWorld(rng=random.Random(1))
    p=w.update_posterior(w.prior,"preprocess_audit","signal")
    assert abs(sum(p.values())-1)<1e-9

def test_eig_nonnegative():
    w=ToyResearchWorld(rng=random.Random(1))
    assert all(w.eig(w.prior,a)>=-1e-10 for a in w.actions)

def test_preprocess_audit_is_diagnostic():
    w=ToyResearchWorld(rng=random.Random(1))
    p=w.update_posterior(w.prior,"preprocess_audit","signal")
    assert p["preprocessing"]==max(p.values())

def test_oracle_valid():
    w=ToyResearchWorld(rng=random.Random(1)); planner=OraclePlanner(w)
    v,d=planner.best_decision(w.prior,w.budget,set(w.actions))
    assert d[0] in {"stop","investigate"}
    assert isinstance(v,float)
