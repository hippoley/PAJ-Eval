from pathlib import Path

ROOT = Path(__file__).parents[1]
HTML = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
LOCALES = (ROOT / "docs" / "locales.js").read_text(encoding="utf-8")
CONTRACT = (ROOT / "V4_DESIGN_CONTRACT.md").read_text(encoding="utf-8")
FAMILIES = (ROOT / "PROBE_FAMILIES.md").read_text(encoding="utf-8")


def test_probe_player_has_ten_locales_from_the_shared_catalog():
    assert 'src="locales.js"' in HTML
    assert "PAJ_LOCALES" in HTML
    for locale in ["en", "zh-CN", "zh-TW", "ja", "ko", "es", "fr", "de", "pt", "ru"]:
        assert f'"{locale}":{{native:' in LOCALES
    assert "Choose the language you think in" in CONTRACT or "locale" in CONTRACT.lower()


def test_all_eight_probe_families_are_playable_from_one_source_of_truth():
    for i in range(1, 9):
        pf = f"PF{i:02d}"
        assert LOCALES.count(pf + ":[") == 10
        assert pf in FAMILIES
    assert "Object.entries(L().pf)" in HTML
    assert "openWorld(id)" in HTML
    assert "finish(j,c)" in HTML
    assert "const PF=[" not in HTML


def test_player_does_not_require_essay_or_one_click_path():
    assert "textarea" not in HTML.lower()
    assert "No required item" not in HTML  # hint is localized instead of hard-coded
    assert "There is no required path" in LOCALES
    assert "No quiz" in LOCALES
    assert "inspect" in HTML
    assert "commit" in HTML


def test_trajectory_is_explicitly_raw_measurement_not_conclusion():
    assert "The trajectory is only the raw sensor" in LOCALES
    assert "Raw events are evidence" in HTML
    for stage in ["versioned derived_features", "versioned evaluations", "counterfactual validation", "treatment comparison"]:
        assert stage in CONTRACT
    assert "A trajectory is a sensor reading, not a conclusion" in FAMILIES


def test_original_paj_question_remains_the_root():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Same task success. Different humans afterward?" in readme
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
