from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = (ROOT / "docs" / "challenge-packs.js").read_text(encoding="utf-8")
HTML = (ROOT / "docs" / "challenge.html").read_text(encoding="utf-8")
CONTRACT = (ROOT / "GOLDEN_DEPTH_CONTRACT.md").read_text(encoding="utf-8")


def test_golden_depth_contract_keeps_journey_not_quiz():
    for phrase in [
        "Seed world",
        "Consequence",
        "Minimal intervention",
        "Near transfer",
        "Far transfer",
        "Raw trajectory",
        "Research inference",
        "Coverage never outranks interaction depth",
    ]:
        assert phrase in CONTRACT


def test_ten_explicit_market_packs_exist():
    expected = {
        '"en":{native:"English · United States"': 'market:"US"',
        '"zh-CN":{native:"简体中文 · 中国"': 'market:"CN"',
        '"zh-TW":{native:"繁體中文 · 台灣"': 'market:"TW"',
        '"ja":{native:"日本語 · 日本"': 'market:"JP"',
        '"ko":{native:"한국어 · 대한민국"': 'market:"KR"',
        '"es":{native:"Español · España"': 'market:"ES"',
        '"fr":{native:"Français · France"': 'market:"FR"',
        '"de":{native:"Deutsch · Deutschland"': 'market:"DE"',
        '"pt":{native:"Português · Brasil"': 'market:"BR"',
        '"ru":{native:"Русский · Россия"': 'market:"RU"',
    }
    for locale_marker, market_marker in expected.items():
        assert locale_marker in PACKS
        assert market_marker in PACKS


def test_market_packs_are_not_currency_only_translations():
    for marker in [
        "广州 → 上海",
        "高雄 → 台北",
        "Seattle → San Francisco",
        "東京 → 新大阪",
        "서울 → 부산",
        "Madrid → Barcelona",
        "Paris → Lyon",
        "Berlin → München",
        "São Paulo → Rio de Janeiro",
        "Москва → Санкт-Петербург",
    ]:
        assert marker in PACKS
    for currency in ["CNY", "TWD", "USD", "JPY", "KRW", "EUR", "BRL", "RUB"]:
        assert f'currency:"{currency}"' in PACKS


def test_each_market_pack_localizes_real_options_not_only_titles():
    # Evidence that action copy, reviews, transport and consequence copy vary by market.
    for phrase in [
        "仍然購買 Lite",
        "Liteのまま購入",
        "Lite 그대로 구매",
        "Seguir con Lite",
        "Garder Lite",
        "Lite behalten",
        "Ficar com Lite",
        "Оставить Lite",
        "Keep Lite",
        "仍然下单",
    ]:
        assert phrase in PACKS
    for phrase in [
        "南港",
        "新大阪",
        "KTX",
        "Fira",
        "Part-Dieu",
        "München Hbf",
        "GIG",
        "Московский вокзал",
    ]:
        assert phrase in PACKS


def test_challenge_preserves_full_golden_interaction_shape():
    for token in [
        'id="shop"',
        'id="checkout"',
        'id="intervention"',
        'id="career"',
        'id="travel"',
        'post_consequence_action',
        'minimal_intervention',
        'open_detail',
        'search_query',
        'careerCommit',
        'travelCommit',
        'session_complete',
    ]:
        assert token in HTML


def test_challenge_is_local_only_and_does_not_pollute_research_backend():
    assert "PAJTransport" not in HTML
    assert "ingest-probe" not in HTML
    assert "supabase" not in HTML.lower()
    assert "golden-challenge-v1" in HTML


def test_participant_surface_does_not_name_probe_constructs():
    for forbidden in [
        "PF01",
        "hidden downstream constraints",
        "latent construct",
        "posterior",
        "oracle",
    ]:
        assert forbidden.lower() not in HTML.lower()
    assert "devMode" in HTML
    assert "Research view" in HTML


def test_localization_contract_requires_affordance_invariance_not_literal_equality():
    for phrase in [
        "behavioral comparability",
        "number of top-level affordances",
        "nested evidence paths",
        "severity and reversibility of the consequence",
        "difficulty of near and far transfer",
        "omission opportunity",
    ]:
        assert phrase in CONTRACT
