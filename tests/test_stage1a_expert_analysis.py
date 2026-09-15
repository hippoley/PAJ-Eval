from pathlib import Path

from analyze_stage1a_experts import flatten, summarize


def _payload():
    return {
        "study": "PAJ-Eval Stage 1A Expert Walkthrough",
        "meta": {"participant_code": "E01"},
        "responses": [
            {"scenario_id": "S17", "top3": ["rerun_seeds", "recompute_metrics", "subgroup_metrics"], "confidence": 80, "realism": 4, "plausible_explanations": "3", "missing_investigation": "", "perceived_leakage": ""},
            {"scenario_id": "S63", "top3": ["rerun_seeds", "recompute_metrics", "subgroup_metrics"], "confidence": 75, "realism": 5, "plausible_explanations": "3", "missing_investigation": "", "perceived_leakage": ""},
            {"scenario_id": "S42", "top3": ["recompute_metrics", "rerun_seeds", "subgroup_metrics"], "confidence": 85, "realism": 4, "plausible_explanations": "3", "missing_investigation": "", "perceived_leakage": ""},
            {"scenario_id": "S88", "top3": ["recompute_metrics", "rerun_seeds", "subgroup_metrics"], "confidence": 80, "realism": 4, "plausible_explanations": "3", "missing_investigation": "", "perceived_leakage": ""},
        ],
    }


def test_expert_analysis_maps_opaque_scenarios_to_counterfactual_worlds():
    rows = flatten([(Path("e01.json"), _payload())])
    assert len(rows) == 4
    assert sum(r["world"] == "A" for r in rows) == 2
    assert sum(r["world"] == "B" for r in rows) == 2


def test_expert_analysis_reports_intended_preference_shift():
    rows = flatten([(Path("e01.json"), _payload())])
    summary = summarize(rows)
    assert summary["global"]["rerun_seed_preference_shift_A_minus_B"] == 1.0
    assert summary["global"]["recompute_metric_preference_shift_B_minus_A"] == 1.0
    assert summary["global"]["median_realism_all"] == 4.0
