import csv
import json

from analyze_latent_question_probe import load_responses, prepare_blind_coding, summarize


def _write_response(path, world, action, started):
    path.write_text(
        json.dumps(
            {
                "instrument": "paj-eval-latent-question-probe-v0.3",
                "world_id": world,
                "rendering_id": "primary",
                "started_at": started,
                "completed_at": started + "Z",
                "pre_menu_snapshot": {"next_free": f"free response {world}"},
                "first_action": action,
                "realism_1_5": "4",
                "ambiguity_1_5": "4",
                "wording_leakage": "",
                "missing_investigation": "",
            }
        ),
        encoding="utf-8",
    )


def test_prepare_and_summarize_blinded_coding(tmp_path):
    responses = tmp_path / "responses"
    responses.mkdir()
    _write_response(responses / "r.json", "R", "embedding_stability_probe", "2026-09-15T12:00:00")
    _write_response(responses / "s.json", "S", "index_freshness_probe", "2026-09-15T12:01:00")

    coding = tmp_path / "coding.csv"
    key = tmp_path / "key.json"
    prepare_blind_coding(load_responses(responses), coding, key)

    with coding.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert "world_id" not in rows[0]
    assert "first_action" not in rows[0]

    for row in rows:
        row["opens_alternative_question_0_1"] = "1"
        row["question_specificity_0_2"] = "2"

    coded_a = tmp_path / "coded_a.csv"
    coded_b = tmp_path / "coded_b.csv"
    for destination in (coded_a, coded_b):
        with destination.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    result = summarize(coded_a, coded_b, key)
    assert result["n_shared"] == 2
    assert result["n_requiring_adjudication"] == 0
    assert result["worlds"]["R"]["mean_blind_opening_score"] == 1.0
    assert result["worlds"]["S"]["mean_blind_specificity_score"] == 2.0
