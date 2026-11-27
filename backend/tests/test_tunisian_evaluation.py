from scripts.evaluate_tunisian import evaluate


def _row(variant: str, score: int) -> dict:
    return {
        "model": "candidate",
        "question_id": f"{variant}-Q01",
        "variant": variant,
        "scores": {criterion: score for criterion in ("comprehension", "intent_preservation", "language_fidelity", "answer_quality")},
    }


def test_tunisian_evaluation_requires_both_variants():
    report = evaluate([_row("tunisian_arabic", 5), _row("arabizi", 3)])

    assert report["winner"] is None
    model = report["models"][0]
    assert model["eligible"] is False
    assert model["rejection_reasons"] == ["arabizi_below_4"]
