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


def test_all_ten_locale_catalogs_are_real_and_complete():
    text = (ROOT / "docs" / "locales.js").read_text(encoding="utf-8")
    assert "||null" not in text
    required = ["en", "zh-CN", "zh-TW", "ja", "ko", "es", "fr", "de", "pt", "ru"]
    for code in required:
        assert f'"{code}":{{native:' in text
    # Every locale must carry every probe family, not only translated shell chrome.
    for pf in [f"PF{i:02d}" for i in range(1, 9)]:
        assert text.count(pf + ":[") == 10


def test_live_player_has_truthful_durable_transport():
    text = (ROOT / "docs" / "live.html").read_text(encoding="utf-8")
    for token in [
        "indexedDB.open",
        "client_submission_id",
        "crypto.randomUUID()",
        "qPut(payload)",
        "retryQueue",
        "probe-player-v4.1",
        "localStorage.setItem('paj_local_trace'",
        "tr().ui.saving",
        "tr().ui.saved",
        "tr().ui.failed",
        "tr().ui.local",
    ]:
        assert token in text


def test_research_browser_is_present_and_does_not_use_service_role():
    path = ROOT / "docs" / "research.html"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "research-sessions" in text
    assert "app_metadata.role = researcher" in text
    assert "SERVICE_ROLE" not in text.upper()


def test_live_page_is_not_the_only_player():
    assert (ROOT / "docs" / "index.html").exists()
    assert (ROOT / "docs" / "live.html").exists()
