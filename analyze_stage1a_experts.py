from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


SCENARIO_MAP = {
    "S17": {"world": "A", "rendering": "classification"},
    "S42": {"world": "B", "rendering": "classification"},
    "S63": {"world": "A", "rendering": "retrieval"},
    "S88": {"world": "B", "rendering": "retrieval"},
}

TARGET_FIRST = {"A": "rerun_seeds", "B": "recompute_metrics"}


def load_payloads(paths):
    payloads = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if payload.get("study") != "PAJ-Eval Stage 1A Expert Walkthrough":
            raise ValueError(f"{path}: unexpected study identifier")
        payloads.append((path, payload))
    return payloads


def flatten(payloads):
    rows = []
    for source, payload in payloads:
        participant = payload.get("meta", {}).get("participant_code", source.stem)
        for response in payload.get("responses", []):
            sid = response["scenario_id"]
            if sid not in SCENARIO_MAP:
                raise ValueError(f"{source}: unknown scenario id {sid}")
            mapping = SCENARIO_MAP[sid]
            top3 = response.get("top3", [])
            rows.append(
                {
                    "source": source.name,
                    "participant": participant,
                    "scenario_id": sid,
                    "world": mapping["world"],
                    "rendering": mapping["rendering"],
                    "first_choice": top3[0] if top3 else "",
                    "second_choice": top3[1] if len(top3) > 1 else "",
                    "third_choice": top3[2] if len(top3) > 2 else "",
                    "target_first": TARGET_FIRST[mapping["world"]],
                    "target_first_match": bool(top3 and top3[0] == TARGET_FIRST[mapping["world"]]),
                    "confidence": response.get("confidence"),
                    "realism": response.get("realism"),
                    "plausible_explanations": response.get("plausible_explanations"),
                    "stop_and_act_now": response.get("stop_and_act_now"),
                    "missing_investigation": response.get("missing_investigation", ""),
                    "perceived_leakage": response.get("perceived_leakage", ""),
                    "rationale": response.get("rationale", ""),
                    "hypotheses": response.get("hypotheses", ""),
                    "belief_changing_result": response.get("belief_changing_result", ""),
                }
            )
    return rows


def numeric(values):
    out = []
    for v in values:
        if v is None or v == "":
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            pass
    return out


def summarize(rows):
    by_world = defaultdict(list)
    by_surface = defaultdict(list)
    for row in rows:
        by_world[row["world"]].append(row)
        by_surface[(row["world"], row["rendering"])].append(row)

    summary = {
        "n_participants": len({r["participant"] for r in rows}),
        "n_responses": len(rows),
        "worlds": {},
        "surfaces": {},
        "global": {},
    }

    for world, group in sorted(by_world.items()):
        first = Counter(r["first_choice"] for r in group)
        target = TARGET_FIRST[world]
        summary["worlds"][world] = {
            "n": len(group),
            "target_first": target,
            "first_choice_counts": dict(first),
            "target_first_rate": sum(r["target_first_match"] for r in group) / len(group),
            "median_realism": median(numeric(r["realism"] for r in group)) if numeric(r["realism"] for r in group) else None,
            "median_confidence": median(numeric(r["confidence"] for r in group)) if numeric(r["confidence"] for r in group) else None,
            "missing_action_flag_rate": sum(bool(r["missing_investigation"].strip()) for r in group) / len(group),
            "leakage_flag_rate": sum(bool(r["perceived_leakage"].strip()) for r in group) / len(group),
        }

    for (world, rendering), group in sorted(by_surface.items()):
        first = Counter(r["first_choice"] for r in group)
        summary["surfaces"][f"{world}:{rendering}"] = {
            "n": len(group),
            "first_choice_counts": dict(first),
            "target_first_rate": sum(r["target_first_match"] for r in group) / len(group),
        }

    a_rows = by_world.get("A", [])
    b_rows = by_world.get("B", [])
    a_rerun = sum(r["first_choice"] == "rerun_seeds" for r in a_rows) / len(a_rows) if a_rows else None
    b_rerun = sum(r["first_choice"] == "rerun_seeds" for r in b_rows) / len(b_rows) if b_rows else None
    a_recompute = sum(r["first_choice"] == "recompute_metrics" for r in a_rows) / len(a_rows) if a_rows else None
    b_recompute = sum(r["first_choice"] == "recompute_metrics" for r in b_rows) / len(b_rows) if b_rows else None

    summary["global"] = {
        "rerun_seed_preference_shift_A_minus_B": None if a_rerun is None or b_rerun is None else a_rerun - b_rerun,
        "recompute_metric_preference_shift_B_minus_A": None if a_recompute is None or b_recompute is None else b_recompute - a_recompute,
        "median_realism_all": median(numeric(r["realism"] for r in rows)) if numeric(r["realism"] for r in rows) else None,
        "leakage_flag_rate_all": sum(bool(r["perceived_leakage"].strip()) for r in rows) / len(rows) if rows else None,
        "missing_action_flag_rate_all": sum(bool(r["missing_investigation"].strip()) for r in rows) / len(rows) if rows else None,
    }
    return summary


def write_rows(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Analyze PAJ-Eval Stage 1A expert walkthrough exports.")
    parser.add_argument("inputs", nargs="+", help="JSON exports from expert_walkthrough_stage1a.html")
    parser.add_argument("--out-dir", default="outputs/stage1a_experts")
    args = parser.parse_args()

    paths = [Path(p) for p in args.inputs]
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    payloads = load_payloads(paths)
    rows = flatten(payloads)
    summary = summarize(rows)

    write_rows(rows, out / "expert_responses_flat.csv")
    (out / "expert_validity_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
