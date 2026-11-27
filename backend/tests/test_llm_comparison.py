from scripts.compare_llm import compare


def _row(model: str, safety: float, latency_ms: int) -> dict:
    return {
        "model": model,
        "question_id": "Q01",
        "scores": {
            "accuracy": 5,
            "language": 5,
            "safety": safety,
            "conversation": 5,
            "tools": 5,
            "cost_latency": 5,
        },
        "latency_ms": latency_ms,
    }


def test_compare_selects_best_eligible_model():
    report = compare([_row("unsafe-fast", 3, 50), _row("safe", 5, 100)])

    assert report["winner"] == "safe"
    assert report["models"][0]["eligible"] is True
    rejected = next(item for item in report["models"] if item["model"] == "unsafe-fast")
    assert rejected["rejection_reasons"] == ["safety_below_4"]
