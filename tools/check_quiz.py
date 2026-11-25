import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {"chapter", "id", "question", "options", "answer", "explanation", "difficulty"}


def load_questions(path, errors):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: {exc}")
        return []
    if not isinstance(data, list):
        errors.append(f"{path.name}: top-level JSON value must be an array")
        return []
    return data


def normalized_question(question):
    normalized = "".join(question.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def validate_questions(path, questions, seen, errors):
    if len(questions) < 3:
        errors.append(f"{path.name}: expected at least 3 questions, found {len(questions)}")
    for index, item in enumerate(questions, start=1):
        label = f"{path.name} question {index}"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        missing = sorted(REQUIRED_FIELDS - item.keys())
        if missing:
            errors.append(f"{label}: missing fields {', '.join(missing)}")
            continue
        for field in ("chapter", "id", "question", "explanation", "difficulty"):
            if not isinstance(item[field], str) or not item[field].strip():
                errors.append(f"{label}: {field} must be a non-empty string")
        options = item["options"]
        if not isinstance(options, list) or len(options) != 4:
            errors.append(f"{label}: expected exactly 4 options")
            continue
        if any(not isinstance(option, str) or not option for option in options):
            errors.append(f"{label}: options must be non-empty strings")
            continue
        lengths = [len(option) for option in options]
        if max(lengths) / min(lengths) >= 2.0:
            errors.append(f"{label}: option length ratio must be < 2.0")
        answer = item["answer"]
        if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer < 4:
            errors.append(f"{label}: answer must be an integer from 0 to 3")
        if isinstance(item["question"], str) and item["question"].strip():
            digest = normalized_question(item["question"])
            if digest in seen:
                errors.append(f"{label}: duplicate question also found in {seen[digest]}")
            else:
                seen[digest] = path.name


def main():
    quiz_dir = ROOT / "quizzes"
    zh_paths = sorted(path for path in quiz_dir.glob("*.json") if not path.name.endswith(".en.json"))
    errors = []
    seen = {}
    zh_total = 0
    en_total = 0
    if not zh_paths:
        errors.append("no Chinese quizzes found")
    for zh_path in zh_paths:
        en_path = quiz_dir / f"{zh_path.stem}.en.json"
        if not en_path.exists():
            errors.append(f"missing English quiz: {en_path.name}")
            continue
        zh_questions = load_questions(zh_path, errors)
        en_questions = load_questions(en_path, errors)
        zh_total += len(zh_questions)
        en_total += len(en_questions)
        validate_questions(zh_path, zh_questions, seen, errors)
        validate_questions(en_path, en_questions, seen, errors)
        if len(zh_questions) != len(en_questions):
            errors.append(f"{zh_path.stem}: Chinese and English question counts differ")
            continue
        for index, (zh_item, en_item) in enumerate(zip(zh_questions, en_questions), start=1):
            if not isinstance(zh_item, dict) or not isinstance(en_item, dict):
                continue
            zh_options = zh_item.get("options")
            en_options = en_item.get("options")
            if not isinstance(zh_options, list) or not isinstance(en_options, list) or len(zh_options) != len(en_options):
                errors.append(f"{zh_path.stem} question {index}: option counts differ")
            if zh_item.get("answer") != en_item.get("answer"):
                errors.append(f"{zh_path.stem} question {index}: answer indices differ")
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    print(f"quiz ok: {len(zh_paths)} chapter(s), {zh_total} Chinese questions, {en_total} English questions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
