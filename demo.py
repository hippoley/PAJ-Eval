import json, random
from pathlib import Path
import pandas as pd
from paj_eval.world import ToyResearchWorld
from paj_eval.oracle import OraclePolicy, OraclePlanner
from paj_eval.policies import GreedyEIGPolicy, ExpensiveBiasPolicy, RandomPolicy

def simulate(n=300, seed=7):
    rows=[]
    factories={
        "oracle": lambda w,r: OraclePolicy(w),
        "greedy_eig": lambda w,r: GreedyEIGPolicy(0.06),
        "expensive_bias": lambda w,r: ExpensiveBiasPolicy(),
        "random": lambda w,r: RandomPolicy(r,0.18),
    }
    for pname,factory in factories.items():
        rng=random.Random(seed)
        for ep in range(n):
            w=ToyResearchWorld(8,rng); p=factory(w,rng); t=w.run_policy(p)
            rows.append({
                "policy":pname,"episode_id":ep,"true_cause":t.true_cause,
                "expected_RU":t.research_utility_expected,"realized_RU":t.research_utility_realized,
                "total_cost":t.total_cost,"total_EIG":t.total_eig,"IAE":t.information_acquisition_efficiency,
                "n_steps":len(t.steps),"terminal_action":t.terminal_action})
    return pd.DataFrame(rows)

if __name__=="__main__":
    out=Path(__file__).parent/"outputs"; out.mkdir(exist_ok=True)
    w=ToyResearchWorld(8,random.Random(1))
    example_posterior=w.posterior_from_initial_clue("slice_anomaly")
    rows=[]
    for name,spec in w.actions.items():
        eig=w.eig(example_posterior,name)
        rows.append({"action":name,"cost":spec.cost,"EIG":eig,"EIG_per_cost":eig/spec.cost})
    diag=pd.DataFrame(rows).sort_values("EIG_per_cost",ascending=False)
    print("Initial action diagnostics\n",diag.round(3).to_string(index=False))
    diag.to_csv(out/"initial_action_diagnostics.csv",index=False)
    planner=OraclePlanner(w)
    ov,od=planner.best_decision(example_posterior,w.budget,set(w.actions))
    print("\nOracle expected utility:",round(ov,3),"first decision:",od)
    df=simulate(300,7)
    summary=df.groupby("policy").agg(
        mean_expected_RU=("expected_RU","mean"),sd_expected_RU=("expected_RU","std"),
        mean_realized_RU=("realized_RU","mean"),mean_cost=("total_cost","mean"),
        mean_EIG=("total_EIG","mean"),mean_IAE=("IAE","mean"),mean_steps=("n_steps","mean")
    ).sort_values("mean_expected_RU",ascending=False)
    print("\nPolicy sanity check\n",summary.round(3).to_string())
    df.to_csv(out/"policy_simulation.csv",index=False); summary.to_csv(out/"policy_summary.csv")
    tw=ToyResearchWorld(8,random.Random(11)); trace=tw.run_policy(GreedyEIGPolicy(0.06))
    (out/"sample_trace.json").write_text(json.dumps(trace.to_dict(),indent=2),encoding="utf-8")
