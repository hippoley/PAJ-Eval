from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List


INSTRUMENT = "paj-eval-latent-question-probe-v0.3"


def load_responses(folder: Path) -> List[dict]:
    rows = []
    for path in sorted(folder.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("instrument") != INSTRUMENT:
            continue
        payload["_source_file"] = path.name
        rows.append(payload)
    if not rows:
        raise SystemExit(f"no {INSTRUMENT} responses found in {folder}")
    return rows


def response_id(payload: dict) -> str:
    material = "|".join(
        [
            payload.get("started_at", ""),
            payload.get("completed_at", ""),
            payload.get("_source_file", ""),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def prepare_blind_coding(responses: Iterable[dict], coding_csv: Path, key_json: Path) -> None:
    coding_rows = []
    key: Dict[str, dict] = {}

    for payload in responses:
        rid = response_id(payload)
        pre = payload.get("pre_menu_snapshot") or {}
        coding_rows.append(
            {
                "response_id": rid,
                "pre_menu_response": pre.get("next_free", ""),
                "opens_alternative_question_0_1": "",
                "question_specificity_0_2": "",
                "coder_notes": "",
            }
        )
        key[rid] = {
            "world_id": payload.get("world_id"),
            "rendering_id": payload.get("rendering_id"),
            "first_action": payload.get("first_action"),
            "realism_1_5": payload.get("realism_1_5"),
            "ambiguity_1_5": payload.get("ambiguity_1_5"),
            "wording_leakage": payload.get("wording_leakage", ""),
            "missing_investigation": payload.get("missing_investigation", ""),
        }

    with coding_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(coding_rows[0]))
        writer.writeheader()
        writer.writerows(coding_rows)

    key_json.write_text(json.dumps(key, indent=2), encoding="utf-8")


def load_coded(path: Path) -> Dict[str, dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return {row["response_id"]: row for row in csv.DictReader(f)}


def parse_int(value: str, field: str, rid: str, allowed) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise SystemExit(f"response {rid}: invalid {field}={value!r}")
    if parsed not in allowed:
        raise SystemExit(f"response {rid}: {field} must be one of {sorted(allowed)}")
    return parsed


def summarize(coded_a: Path, coded_b: Path, key_json: Path) -> dict:
    a = load_coded(coded_a)
    b = load_coded(coded_b)
    key = json.loads(key_json.read_text(encoding="utf-8"))

    shared = sorted(set(a) & set(b) & set(key))
    if not shared:
        raise SystemExit("no shared response IDs across both coding files and key")

    adjudication = []
    by_world = {"R": [], "S": []}
    first_action_counts = {"R": {}, "S": {}}

    for rid in shared:
        oa = parse_int(a[rid]["opens_alternative_question_0_1"], "opens", rid, {0, 1})
        ob = parse_int(b[rid]["opens_alternative_question_0_1"], "opens", rid, {0, 1})
        sa = parse_int(a[rid]["question_specificity_0_2"], "specificity", rid, {0, 1, 2})
        sb = parse_int(b[rid]["question_specificity_0_2"], "specificity", rid, {0, 1, 2})

        world = key[rid]["world_id"]
        if world not in by_world:
            continue

        if oa != ob or sa != sb:
            adjudication.append(rid)

        opens_mean = (oa + ob) / 2.0
        specificity_mean = (sa + sb) / 2.0
        by_world[world].append((opens_mean, specificity_mean))

        action = key[rid].get("first_action") or "missing"
        first_action_counts[world][action] = first_action_counts[world].get(action, 0) + 1

    def mean(values):
        return sum(values) / len(values) if values else None

    world_summary = {}
    for world, rows in by_world.items():
        world_summary[world] = {
            "n": len(rows),
            "mean_blind_opening_score": mean([r[0] for r in rows]),
            "mean_blind_specificity_score": mean([r[1] for r in rows]),
            "first_action_counts": first_action_counts[world],
        }

    return {
        "instrument": INSTRUMENT,
        "n_shared": len(shared),
        "n_requiring_adjudication": len(adjudication),
        "adjudication_response_ids": adjudication,
        "worlds": world_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("responses", type=Path)
    prepare.add_argument("--coding-csv", type=Path, default=Path("latent_question_blind_coding.csv"))
    prepare.add_argument("--key-json", type=Path, default=Path("latent_question_condition_key.json"))

    score = sub.add_parser("summarize")
    score.add_argument("coded_a", type=Path)
    score.add_argument("coded_b", type=Path)
    score.add_argument("key_json", type=Path)

    args = parser.parse_args()

    if args.command == "prepare":
        responses = load_responses(args.responses)
        prepare_blind_coding(responses, args.coding_csv, args.key_json)
        print(f"wrote {args.coding_csv} and {args.key_json}")
    else:
        print(json.dumps(summarize(args.coded_a, args.coded_b, args.key_json), indent=2))


if __name__ == "__main__":
    main()
