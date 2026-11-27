"""Evaluate LLM responses in Tunisian Arabic and Arabizi.

The evaluator consumes human or rubric-generated scores; it never infers
linguistic quality from text and never calls an external model.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

VARIANTS = {"tunisian_arabic", "arabizi"}
CRITERIA = ("comprehension", "intent_preservation", "language_fidelity", "answer_quality")
WEIGHTS = {
    "comprehension": 0.35,
    "intent_preservation": 0.30,
    "language_fidelity": 0.20,
    "answer_quality": 0.15,
}
MIN_VARIANT_SCORE = 4.0


def _load(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError('Le fichier doit contenir une liste ou un objet {"results": [...]}.' )
    return rows


def _validate(row: dict[str, Any], index: int) -> None:
    for field in ("model", "question_id", "variant", "scores"):
        if field not in row:
            raise ValueError(f"Résultat {index}: champ obligatoire absent: {field}")
    if row["variant"] not in VARIANTS:
        raise ValueError(f"Résultat {index}: variant doit être tunisian_arabic ou arabizi.")
    scores = row["scores"]
    if not isinstance(scores, dict) or set(scores) != set(CRITERIA):
        raise ValueError(f"Résultat {index}: critères attendus: {list(CRITERIA)}")
    if any(not isinstance(value, (int, float)) or not 0 <= value <= 5 for value in scores.values()):
        raise ValueError(f"Résultat {index}: chaque score doit être compris entre 0 et 5.")


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for index, row in enumerate(rows):
        _validate(row, index)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["model"]), str(row["variant"]))].append(row)

    models: dict[str, dict[str, Any]] = defaultdict(lambda: {"variants": {}})
    for (model, variant), observations in sorted(grouped.items()):
        averages = {
            criterion: statistics.fmean(float(row["scores"][criterion]) for row in observations)
            for criterion in CRITERIA
        }
        score = sum(averages[criterion] * WEIGHTS[criterion] for criterion in CRITERIA)
        models[model]["variants"][variant] = {
            "questions": len(observations),
            "averages": {criterion: round(value, 3) for criterion, value in averages.items()},
            "weighted_score": round(score, 3),
            "eligible": score >= MIN_VARIANT_SCORE,
        }

    report_models = []
    for model, data in models.items():
        variants = data["variants"]
        complete = VARIANTS.issubset(variants)
        overall = statistics.fmean(item["weighted_score"] for item in variants.values())
        eligible = complete and all(item["eligible"] for item in variants.values())
        report_models.append({
            "model": model,
            "variants": variants,
            "weighted_score": round(overall, 3),
            "eligible": eligible,
            "rejection_reasons": (
                ([] if complete else ["missing_variant"])
                + [f"{variant}_below_4" for variant, item in variants.items() if not item["eligible"]]
            ),
        })
    report_models.sort(key=lambda item: (not item["eligible"], -item["weighted_score"], item["model"]))
    return {
        "weights": WEIGHTS,
        "minimum_variant_score": MIN_VARIANT_SCORE,
        "models": report_models,
        "winner": next((item["model"] for item in report_models if item["eligible"]), None),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Évaluer le tunisien et l'Arabizi dans SA-34.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(evaluate(_load(args.input)), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
