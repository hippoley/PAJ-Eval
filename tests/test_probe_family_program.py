from pathlib import Path

ROOT = Path(__file__).parents[1]
FAMILIES = (ROOT / "PROBE_FAMILIES.md").read_text(encoding="utf-8")
LOOP = (ROOT / "EVALUATION_LOOP.md").read_text(encoding="utf-8")


def test_every_family_is_named_and_bounded():
    names = [
        "Hidden downstream constraints",
        "Competing causal frames",
        "Omitted evidence",
        "Anomaly triage",
        "Experiment selection",
        "Premature stopping",
        "Wrong-problem detection",
        "Cross-domain spontaneous opening",
    ]
    for name in names:
        assert name in FAMILIES


def test_evaluation_loop_ends_in_policy_comparison_not_personality_scoring():
    for stage in [
        "Raw trajectory",
        "Behavioral features",
        "Construct",
        "Score",
        "Counterfactual validity",
        "Treatment effect",
    ]:
        assert stage in LOOP
    assert "Frame-first versus Self-frame-first" in LOOP
    assert "single session does not establish learning" in LOOP


def test_raw_trace_is_not_circularly_labeled():
    assert "raw trace should not contain hidden semantic labels" in LOOP
    assert "generic diligence" in LOOP
    assert "rival explanations" in LOOP
