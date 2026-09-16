from pathlib import Path

ROOT = Path(__file__).parents[1]
HTML = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
FAMILIES = (ROOT / "PROBE_FAMILIES.md").read_text(encoding="utf-8")


def test_probe_player_has_ten_locales():
    for locale in ["en", "zh-CN", "zh-TW", "ja", "ko", "es", "fr", "de", "pt", "ru"]:
        assert f"{locale}:" in HTML or f"'{locale}':" in HTML
    assert "CHOOSE THE LANGUAGE YOU THINK IN" in HTML


def test_all_eight_probe_families_are_playable():
    for i in range(1, 9):
        assert f"PF{i:02d}" in HTML
        assert f"PF{i:02d}" in FAMILIES
    assert "startPF" in HTML
    assert "openObj" in HTML
    assert "commit" in HTML


def test_player_does_not_require_essay_or_one_click_path():
    assert "textarea" not in HTML.lower()
    assert "There is no required path" in HTML
    assert "Opening more things is not automatically better" in HTML
    assert "No quiz" in HTML


def test_trajectory_is_explicitly_raw_measurement_not_conclusion():
    assert "The trajectory is only the raw sensor" in HTML
    for stage in ["Trajectory", "Features", "Construct", "Score", "Counterfactual", "Treatment effect"]:
        assert stage in HTML
    assert "Not yet a validated score" in HTML
    assert "A trajectory is a sensor reading, not a conclusion" in FAMILIES


def test_original_paj_question_remains_the_root():
    assert "Same task success can hide different future humans" in HTML
    assert "after AI assistance is removed" in FAMILIES
    assert "None of them alone is PAJ-Eval" in FAMILIES


def test_family_growth_requires_falsification_not_just_more_scenarios():
    required = [
        "counterfactual twin",
        "surface-invariance",
        "omitted-action audit",
        "no-answer-cue audit",
        "overreach or negative-transfer world",
        "blind expert-coherence check",
        "preregistered construct/score",
    ]
    for phrase in required:
        assert phrase in FAMILIES


def test_multilingual_is_measurement_validity_not_decoration():
    assert "Localization is part of measurement validity, not decoration" in FAMILIES
    for phrase in ["semantic-equivalence", "cue strength", "action affordances", "Cross-language invariance"]:
        assert phrase in FAMILIES
