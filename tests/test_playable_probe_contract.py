from pathlib import Path

HTML = (Path(__file__).parents[1] / "docs" / "index.html").read_text(encoding="utf-8")
SPEC = (Path(__file__).parents[1] / "INCEPTION_PLAYGROUND_V1.md").read_text(encoding="utf-8")


def test_experience_starts_with_action_not_explanation():
    assert "90-second cognitive experiment" in HTML
    assert "I won't ask you to explain yourself" in HTML
    assert "What would you do first, and why?" not in HTML
    assert "textarea" not in HTML.lower()


def test_vertical_slice_contains_baseline_intervention_and_transfer():
    for screen in ['id="shop"', 'id="consequence"', 'id="inception"', 'id="career"', 'id="transfer"']:
        assert screen in HTML
    assert "intervention_exposed" in HTML
    assert "after_intervention:true" in HTML


def test_probe_is_behavioral_and_world_embedded():
    assert "Inspect first:" in HTML
    assert "Compatibility" in HTML
    assert "Look closer" in HTML
    assert "Ground transport" in HTML
    assert "inspect" in HTML
    assert "commit" in HTML


def test_intervention_is_minimal_and_then_removed():
    assert "what does this decision make easy—or expensive—later?" in HTML
    career = HTML.split('id="career"', 1)[1].split('id="transfer"', 1)[0]
    travel = HTML.split('id="transfer"', 1)[1].split('id="done"', 1)[0]
    assert "easy—or expensive—later" not in career
    assert "easy—or expensive—later" not in travel


def test_trace_and_profile_exist_but_are_marked_prototype():
    assert "BEHAVIOR TRACE" in HTML
    assert "inception transfer profile · local preview" in HTML
    assert "not a judgment about you" in HTML
    assert "inception-playground-v1" in HTML


def test_research_contract_preserves_core_invariants():
    required = [
        "No essay-first elicitation",
        "target cognitive structure is never named before baseline",
        "Intervention is minimal",
        "intervention is then removed",
        "Transfer worlds change surface and domain",
        "over-application must be measured",
    ]
    for phrase in required:
        assert phrase in SPEC
