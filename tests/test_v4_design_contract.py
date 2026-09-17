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
        "server-side idempotency verification",
        "Operational release",
        "authenticated browser replay",
        "JWT/role boundary",
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
        "probe-player-v4.4",
        "localStorage.setItem('paj_local_trace'",
        "Research Session Browser",
    ]:
        assert token in index
    for token in ["indexedDB.open", "queue.put(item)", "retryAll", "inFlight", "created_at_client"]:
        assert token in transport
    assert "const PF=[" not in index
    assert "const L={" not in index


def test_canonical_player_preserves_golden_natural_world_interaction():
    index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    # Interaction should feel like navigating a real application, not pressing
    # researcher-labelled diagnostic buttons.
    for token in [
        "NAVIGABLE MICRO-WORLDS",
        "renderNav",
        "renderView",
        "open_object",
        "search_query",
        "HOME HUB LITE",
        "Buyer reviews",
        "release.log",
        "serving B",
        "Vendor A / critical condition",
        "Support tickets",
        "Remaining budget",
        "Rollback available",
        "Original request",
        "Stakeholder note",
    ]:
        assert token in index
    assert "latent cause" not in index.lower()
    assert "posterior" not in index.lower()
    assert "oracle" not in index.lower()


def test_golden_journey_remains_available_as_non_regression_reference():
    journey = (ROOT / "docs" / "journey.html").read_text(encoding="utf-8")
    for token in [
        "SMART HOME SHOP",
        "我的设备",
        "买家评价",
        "配送与退换",
        "MAIL / OFFERS",
        "TRIP PLANNER",
        "一个选择，会改变后面还剩下哪些选择",
    ]:
        assert token in journey


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


def test_research_browser_replays_multiple_probe_runs_and_supports_deep_links():
    text = (ROOT / "docs" / "research.html").read_text(encoding="utf-8")
    for token in [
        "eventsByRun",
        "featuresByRun",
        "renderRun",
        "Run-by-run replay",
        "session_id",
        "history.replaceState",
        "Open session ID",
        "orphanEvents",
    ]:
        assert token in text
    assert "runs[0]" not in text


def test_synthetic_transport_test_is_part_of_ci():
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    test_js = (ROOT / "tests" / "transport.test.js").read_text(encoding="utf-8")
    assert "node --test tests/transport.test.js" in workflow
    assert "queue commit precedes the first network attempt" in test_js
    assert "concurrent duplicate submission is coalesced" in test_js
    assert "retry preserves queue order" in test_js


def test_backend_ingestion_is_atomic_and_server_idempotent():
    migration = (ROOT / "supabase" / "migrations" / "20260917_atomic_probe_ingestion_v2.sql").read_text(encoding="utf-8")
    edge = (ROOT / "supabase" / "functions" / "ingest-probe" / "index.ts").read_text(encoding="utf-8")
    for token in [
        "ingest_probe_atomic",
        "on conflict (client_submission_id)",
        "jsonb_array_elements(p_events) with ordinality",
        "grant execute on function",
        "service_role",
    ]:
        assert token in migration.lower()
    for token in [
        'sb.rpc("ingest_probe_atomic"',
        "ALLOWED_LOCALES",
        "payload_too_large",
        "client_submission_id",
        "PF0[1-8]",
    ]:
        assert token in edge
    assert '.from("sessions").insert' not in edge
    assert '.from("events").insert' not in edge


def test_research_api_is_role_gated_orders_events_and_fails_closed():
    edge = (ROOT / "supabase" / "functions" / "research-sessions" / "index.ts").read_text(encoding="utf-8")
    for token in [
        'sb.auth.getUser(token)',
        'user.app_metadata?.role!=="researcher"',
        'eq("session_id",sessionId)',
        'order("seq")',
        'derived_features',
        'evaluations',
        'error:"invalid_session_id"',
        'error:"research_read_failed"',
        'Promise.all([',
    ]:
        assert token in edge
    assert 'Access-Control-Allow-Methods":"GET,OPTIONS"' in edge


def test_deployment_doc_keeps_researcher_smoke_gate_explicit():
    text = (ROOT / "DEPLOYMENT_CONFIG.md").read_text(encoding="utf-8")
    for token in [
        "duplicate=false",
        "duplicate=true",
        "same session id",
        "zero",
        "app_metadata.role = researcher",
        "research_read_failed",
    ]:
        assert token.lower() in text.lower()
