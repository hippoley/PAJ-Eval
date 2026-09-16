from pathlib import Path


HTML = (Path(__file__).parents[1] / "docs" / "index.html").read_text(encoding="utf-8")


def test_task_contract_is_explicit():
    assert "HUMAN PARTICIPANT" in HTML
    assert "You — not an AI model" in HTML
    assert "Unavailable in this task" in HTML
    assert "7 investigation credits" in HTML
    assert "Good decision under limited evidence" in HTML


def test_probe_is_action_first_not_essay_first():
    assert "What would you do first, and why?" not in HTML
    assert "openingText" not in HTML
    assert "first move" not in HTML.lower()
    assert "Where do you look next?" in HTML
    assert "DECIDE ANYTIME" in HTML


def test_world_has_costs_consequences_and_stopping():
    assert "budget_before" in HTML
    assert "budget_after" in HTML
    assert "finding:F[s.world][id]" in HTML
    assert "Defer / escalate" in HTML
    assert "More evidence is not automatically better" in HTML


def test_no_correctness_feedback_during_play():
    forbidden = ["correct answer", "incorrect answer", "you are correct", "you are wrong"]
    lower = HTML.lower()
    for phrase in forbidden:
        assert phrase not in lower


def test_trace_identifies_human_no_ai_instrument():
    assert "participant:'human'" in HTML
    assert "ai_available:false" in HTML
    assert "paj-playable-probe-v2" in HTML
