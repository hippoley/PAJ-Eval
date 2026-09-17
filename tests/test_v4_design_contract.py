from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_design_contract_preserves_full_instrument():
    text = (ROOT / "V4_DESIGN_CONTRACT.md").read_text(encoding="utf-8")
    for token in [
        "PF01-PF08",
        "append-only events",
        "versioned derived_features",
        "versioned evaluations",
        "session replay",
        "counterfactual validation",
        "treatment comparison",
        "local only",
        "saving",
        "saved",
        "save failed",
        "IndexedDB",
        "Research Session Browser",
    ]:
        assert token in text


def test_locale_catalog_does_not_claim_null_locales_are_complete():
    text = (ROOT / "docs" / "locales.js").read_text(encoding="utf-8")
    # This intentionally fails until all ten scenario-level catalogs are real.
    assert "window.PAJ_LOCALES[code]=window.PAJ_LOCALES[code]||null" not in text


def test_live_page_is_not_the_only_player():
    assert (ROOT / "docs" / "index.html").exists()
    assert (ROOT / "docs" / "live.html").exists()
