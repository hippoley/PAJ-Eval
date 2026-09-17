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
    for pf in [f"PF{i:02d}" for i in range(1, 9)]:
        assert text.count(pf + ":[") == 10


def test_canonical_player_uses_shared_catalog_and_transport():
    index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    transport = (ROOT / "docs" / "transport.js").read_text(encoding="utf-8")
    for token in [
        'src="locales.js"',
        'src="transport.js"',
        "PAJ_LOCALES",
        "PAJTransport.createBrowserTransport",
        "client_submission_id",
        "crypto.randomUUID()",
        "probe-player-v4.1",
        "localStorage.setItem('paj_local_trace'",
        "Research Session Browser",
    ]:
        assert token in index
    for token in ["indexedDB.open", "queue.put(item)", "retryAll", "inFlight", "created_at_client"]:
        assert token in transport
    # Prevent a second embedded catalog/player implementation from drifting again.
    assert "const PF=[" not in index
    assert "const L={" not in index


def test_live_surface_is_only_a_compatibility_alias():
    text = (ROOT / "docs" / "live.html").read_text(encoding="utf-8")
    assert "index.html?surface=live" in text
    assert "indexedDB.open" not in text
    assert "const ENDPOINT" not in text


def test_research_browser_is_present_and_does_not_use_service_role():
    path = ROOT / "docs" / "research.html"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "research-sessions" in text
    assert "app_metadata.role = researcher" in text
    assert "SERVICE_ROLE" not in text.upper()


def test_synthetic_transport_test_is_part_of_ci():
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "node --test tests/transport.test.js" in workflow
    assert (ROOT / "tests" / "transport.test.js").exists()
