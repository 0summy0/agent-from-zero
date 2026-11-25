import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FIELDS = {
    "id",
    "title_zh",
    "title_en",
    "prereq",
    "est_minutes",
    "ram_min_mb",
    "needs_api_key",
    "source_revision",
}


def run_tool(name):
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / name)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def assert_tool_succeeds(name):
    result = run_tool(name)
    assert result.returncode == 0, result.stdout + result.stderr


def test_at_least_one_chapter_exists():
    assert list((ROOT / "docs" / "zh").glob("*.md")), "at least one Chinese chapter is required"


def test_bilingual_chapter_ids_match():
    zh_ids = {path.stem for path in (ROOT / "docs" / "zh").glob("*.md")}
    en_ids = {path.stem for path in (ROOT / "docs" / "en").glob("*.md")}
    assert zh_ids == en_ids


def test_bilingual_code_fingerprints_and_revisions_match():
    assert_tool_succeeds("check_parity.py")


def test_dependency_bounds():
    assert_tool_succeeds("check_bounds.py")


def test_quiz_contract():
    assert_tool_succeeds("check_quiz.py")


def test_front_matter_fields():
    paths = list((ROOT / "docs" / "zh").glob("*.md")) + list((ROOT / "docs" / "en").glob("*.md"))
    assert paths
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"missing front-matter: {path.name}"
        fields = {
            line.split(":", 1)[0].strip()
            for line in text.split("---", 2)[1].splitlines()
            if ":" in line
        }
        assert REQUIRED_FIELDS <= fields, f"missing front-matter fields: {path.name}"
