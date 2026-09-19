from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PACKS = (ROOT / "docs" / "challenge-packs.js").read_text(encoding="utf-8")
DEPTH = (ROOT / "docs" / "challenge-depth.js").read_text(encoding="utf-8")
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


def test_depth_copy_exists_for_every_market_and_changes_real_consequences():
    for locale in ["en", "zh-CN", "zh-TW", "ja", "ko", "es", "fr", "de", "pt", "ru"]:
        assert f'"{locale}":{{' in DEPTH
    for token in [
        "proConsequence",
        "proLine1",
        "mobility",
        "lateNotice",
        "earlyNotice",
        "transportExtra",
        "hotelExtra",
        "morningExtra",
    ]:
        assert DEPTH.count(token + ':') == 10
    for localized in [
        "今晚送达这件事变了",
        "今晚到貨這件事改變了",
        "Same-day delivery just changed",
        "今夜届くという条件が変わりました",
        "오늘 배송 조건이 바뀌었습니다",
        "La entrega de hoy acaba de cambiar",
        "La livraison ce soir vient de changer",
        "Die Lieferung für heute hat sich geändert",
        "A entrega de hoje mudou",
        "Условие доставки на сегодня изменилось",
    ]:
        assert localized in DEPTH


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


def test_transfer_worlds_have_nested_objects_and_a_revisable_far_transfer_commit():
    for token in [
        'class="btn mobility"',
        "careerDetail(b.dataset.k,'mobility')",
        "provisional_commit",
        "renderTravelHold",
        "arrival_plan",
        "switch_time",
        "finalizeTravel",
        "object:b.dataset.kind+'_nested'",
        "D.travel.transportExtra",
        "D.travel.hotelExtra",
        "D.travel.morningExtra",
    ]:
        assert token in HTML
    assert "travelDraft" in HTML
    assert "travelExpanded" in HTML


def test_seed_consequence_exists_for_both_product_paths():
    assert "S.consequence=p.kind==='lite'?'bridge':'delivery'" in HTML
    assert "D.checkout.proConsequence" in HTML
    assert "D.checkout.proLine1" in HTML
    assert "affected_devices" in HTML
    assert "alternative_models" in HTML
    assert "tomorrow_delivery" in HTML
    assert "pickup_tonight" in HTML


def test_challenge_is_local_only_and_does_not_pollute_research_backend():
    assert "PAJTransport" not in HTML
    assert "ingest-probe" not in HTML
    assert "supabase" not in HTML.lower()
    assert "golden-challenge-v2" in HTML


def test_participant_surface_does_not_name_probe_constructs():
    visible = re.sub(r"<script[\s\S]*?</script>", " ", HTML, flags=re.I)
    visible = re.sub(r"<style[\s\S]*?</style>", " ", visible, flags=re.I)
    visible = re.sub(r"<[^>]+>", " ", visible)
    for forbidden in [
        "PF01",
        "hidden downstream constraints",
        "posterior",
        "oracle",
    ]:
        assert forbidden.lower() not in visible.lower()
    assert "devMode" in HTML
    assert "Research view" in HTML
    assert 'id="researchBox" class="research hidden"' in HTML


def test_localization_contract_requires_affordance_invariance_not_literal_equality():
    contract = CONTRACT.lower()
    for phrase in [
        "behavioral comparability",
        "number of top-level affordances",
        "nested evidence paths",
        "severity and reversibility of the consequence",
        "difficulty of near and far transfer",
        "omission opportunity",
    ]:
        assert phrase in contract


def test_formal_trace_does_not_record_free_form_search_text():
    assert "query:q" not in HTML
    assert "query:value" not in HTML
    assert "query_chars:value.length" in HTML


def test_pf01_uses_real_application_surface_patterns():
    for token in [
        "productGrid",
        "productVisual",
        "deviceList",
        "searchSuggestions",
        "checkoutFlow",
        "mailList",
        "offerSheet",
        "mapCompare",
        "travelGrid",
        "timeline",
    ]:
        assert token in HTML


def test_pf01_search_is_free_form_but_does_not_persist_query_text():
    assert 'id="storeSearchQ"' in HTML
    assert "query_chars:value.length" in HTML
    assert "query:value" not in HTML
    assert "query:q" not in HTML


def test_checkout_has_one_decision_problem_per_screen():
    for token in [
        "checkoutDecisionTitle",
        "decisionOptions",
        "chooseLiteBridge",
        "choosePro",
        "chooseTomorrow",
        "choosePickup",
        "alternativeLink",
        "evidenceLink",
    ]:
        assert token in HTML
    assert "id="change"" not in HTML
    assert "id="inspect"" not in HTML


def test_checkout_inspection_is_not_counted_as_revision():
    assert "if(a==='inspect_devices'){showAffectedDevices();return}" in HTML
    assert "if(a==='other_models'){showAlternativeModels();return}" in HTML
    assert "post_consequence_action',{world:'shop',action:'accept_bridge'" in HTML
    assert "post_consequence_action',{world:'shop',action:'tomorrow_delivery'" in HTML
    assert "post_consequence_action',{world:'shop',action:'pickup_tonight'" in HTML
