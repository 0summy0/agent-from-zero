import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_1_4_hallucination",
    ROOT / "chapters" / "stage1-how-lm-works" / "hallucination.py",
)
hallucination = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hallucination)


def test_chapter_module_imports():
    assert hallucination.CHAPTER_ID == "1.4-hallucination"
    assert callable(hallucination.run_minimal_path)
    assert callable(hallucination.answer_with_evidence)


def test_knowledge_base_question_returns_supporting_evidence():
    result = hallucination.answer_with_evidence(
        "What is the capital of France?", hallucination.KNOWLEDGE_BASE
    )
    assert result["status"] == "grounded"
    assert result["evidence"]
    assert result["evidence"][0]["id"] == "kb-capital-france"
    assert result["evidence"][0]["text"] in result["answer"]
    assert result["evidence"][0]["id"] in result["answer"]


def test_outside_question_abstains_instead_of_inventing():
    result = hallucination.answer_with_evidence(
        "What is the capital of Atlantis?", hallucination.KNOWLEDGE_BASE
    )
    assert result["status"] == "abstain"
    assert result["evidence"] == []
    assert "don't know" in result["answer"].lower()
    assert "more information" in result["answer"].lower()


def test_combined_question_needs_one_supporting_record():
    result = hallucination.answer_with_evidence(
        "What is the capital of France and Canada?", hallucination.KNOWLEDGE_BASE
    )
    assert result["status"] == "abstain"
    assert result["evidence"] == []


def test_evidence_ids_are_nonempty():
    for item in hallucination.KNOWLEDGE_BASE:
        assert isinstance(item["id"], str)
        assert item["id"].strip()
        result = hallucination.answer_with_evidence(item["title"], hallucination.KNOWLEDGE_BASE)
        assert result["evidence"]
        assert all(evidence["id"].strip() for evidence in result["evidence"])


def test_minimal_path_is_deterministic_and_json_serializable():
    first = hallucination.run_minimal_path()
    second = hallucination.run_minimal_path()
    assert first == second
    assert json.loads(json.dumps(first)) == first
    assert first["grounded_case"]["status"] == "grounded"
    assert first["abstention_case"]["status"] == "abstain"
