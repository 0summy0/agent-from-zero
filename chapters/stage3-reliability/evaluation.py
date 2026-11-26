import json

CHAPTER_ID = "3.1-evaluation"

# A tiny, fixed dataset: no downloads, model calls, or random sampling.
EVALUATION_SET = [
    {
        "id": "arithmetic",
        "input": "What is 2 + 2?",
        "expected_answer": "4",
        "aliases": ["four"],
    },
    {
        "id": "geography",
        "input": "What is the capital of France?",
        "expected_answer": "Paris",
        "aliases": ["City of Light"],
    },
    {
        "id": "color",
        "input": "What color is grass?",
        "expected_answer": "green",
        "aliases": ["verdant"],
    },
    {
        "id": "calendar",
        "input": "How many days are in a week?",
        "expected_answer": "7",
        "aliases": ["seven"],
    },
]

TOY_ANSWERS = ["4", "paris", "blue", "SEVEN"]


def normalize_text(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return " ".join(text.casefold().split())


def exact_match(prediction, expected_answer, aliases=()):
    """Compare normalized text with an expected answer or one of its aliases."""
    normalized_prediction = normalize_text(prediction)
    return any(
        normalized_prediction == normalize_text(candidate)
        for candidate in (expected_answer, *aliases)
    )


def contains_expected(prediction, expected_answer):
    """Check whether a normalized expected answer occurs in the prediction."""
    return normalize_text(expected_answer) in normalize_text(prediction)


def evaluate(dataset, predictions, strategy="exact"):
    """Return a JSON-serializable report for equally sized dataset and answers."""
    if not dataset:
        raise ValueError("dataset must not be empty")
    if strategy not in {"exact", "contains"}:
        raise ValueError("strategy must be 'exact' or 'contains'")
    if len(predictions) != len(dataset):
        raise ValueError("predictions must have one answer per dataset item")

    results = []
    for item, prediction in zip(dataset, predictions, strict=True):
        if strategy == "exact":
            passed = exact_match(prediction, item["expected_answer"], item.get("aliases", ()))
        else:
            passed = contains_expected(prediction, item["expected_answer"])
        results.append(
            {
                "id": item["id"],
                "input": item["input"],
                "expected_answer": item["expected_answer"],
                "prediction": prediction,
                "passed": passed,
            }
        )

    passed_count = sum(item["passed"] for item in results)
    return {
        "total": len(results),
        "passed": passed_count,
        "pass_rate": passed_count / len(results),
        "results": results,
    }


def run_minimal_path():
    report = evaluate(EVALUATION_SET, TOY_ANSWERS)
    return {
        "chapter": CHAPTER_ID,
        "strategy": "exact",
        "dataset_size": report["total"],
        "pass_rate": report["pass_rate"],
        "results": report["results"],
    }


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
