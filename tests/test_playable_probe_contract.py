from pathlib import Path

HTML = (Path(__file__).parents[1] / "docs" / "index.html").read_text(encoding="utf-8")
SPEC = (Path(__file__).parents[1] / "INCEPTION_PLAYGROUND_V1.md").read_text(encoding="utf-8")


def test_user_knows_how_to_act_without_research_language():
    assert "按你平时真的会做的方式来" in HTML
    assert "每个按钮都只是它字面上的现实动作" in HTML
    assert "没有必经流程" in HTML
    assert "textarea" not in HTML.lower()


def test_frontend_exposes_real_objects_not_latent_variables():
    for label in ["我的设备", "买家评价", "配送与退换", "收件箱", "公司资料", "日历", "地图", "机场", "酒店"]:
        assert label in HTML
    # The participant UI must not offer the latent construct itself as a button.
    forbidden_buttons = [">兼容性<", ">隐藏成本<", ">未来选择<", ">Look closer<"]
    for phrase in forbidden_buttons:
        assert phrase not in HTML


def test_behavior_and_inference_are_separate_layers():
    assert "open_object" in HTML
    assert "open_detail" in HTML
    assert "commit" in HTML
    assert "const tags=" in HTML
    assert "function infer()" in HTML
    assert "当前竞争解释" in HTML
    assert "系统没有要求你点击" in HTML


def test_no_single_required_path():
    assert "想看什么就打开什么" in HTML
    assert "觉得信息够了就直接做决定" in HTML
    assert "直接买" in HTML
    assert "可以直接回复，也可以自己翻资料" in HTML


def test_intervention_is_experiential_and_fades():
    assert "一个选择，会改变后面还剩下哪些选择" in HTML
    career = HTML.split('id="career"', 1)[1].split('id="travel"', 1)[0]
    travel = HTML.split('id="travel"', 1)[1].split('id="done"', 1)[0]
    assert "一个选择，会改变后面还剩下哪些选择" not in career
    assert "一个选择，会改变后面还剩下哪些选择" not in travel


def test_trace_is_local_prototype_not_validated_score():
    assert "inception-natural-world-v2" in HTML
    assert "原型推断，不是人格评分" in HTML
    assert "latent_preview" in HTML


def test_research_contract_core_invariants_still_hold():
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
