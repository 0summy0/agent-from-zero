import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
FENCE_PATTERN = re.compile(r"^```[^\n]*\n(.*?)^```[\t ]*$", re.MULTILINE | re.DOTALL)
HEADING_PATTERN = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def code_blocks(text):
    return FENCE_PATTERN.findall(text)


def normalize_code(block):
    lines = []
    for line in block.strip().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("//"):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def fingerprints(text):
    return [
        hashlib.sha256(normalize_code(block).encode("utf-8")).hexdigest()
        for block in code_blocks(text)
    ]


def front_matter(text):
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fields = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def validate():
    zh_dir = ROOT / "docs" / "zh"
    en_dir = ROOT / "docs" / "en"
    zh_paths = {path.stem: path for path in zh_dir.glob("*.md")}
    en_paths = {path.stem: path for path in en_dir.glob("*.md")}
    errors = []
    if not zh_paths:
        errors.append("no Chinese chapters found")
    if zh_paths.keys() != en_paths.keys():
        errors.append(f"chapter id mismatch: zh={sorted(zh_paths)}, en={sorted(en_paths)}")
    for chapter_id in sorted(zh_paths.keys() & en_paths.keys()):
        zh_text = zh_paths[chapter_id].read_text(encoding="utf-8")
        en_text = en_paths[chapter_id].read_text(encoding="utf-8")
        if fingerprints(zh_text) != fingerprints(en_text):
            errors.append(f"code fingerprint mismatch: {chapter_id}")
        zh_headings = len(HEADING_PATTERN.findall(FENCE_PATTERN.sub("", zh_text)))
        en_headings = len(HEADING_PATTERN.findall(FENCE_PATTERN.sub("", en_text)))
        if abs(zh_headings - en_headings) > 1:
            errors.append(
                f"heading count mismatch: {chapter_id}: zh={zh_headings}, en={en_headings}"
            )
        for language, text in (("zh", zh_text), ("en", en_text)):
            fields = front_matter(text)
            missing = sorted(REQUIRED_FIELDS - fields.keys())
            if missing:
                errors.append(
                    f"front-matter missing fields: {language}/{chapter_id}: {', '.join(missing)}"
                )
        zh_revision = front_matter(zh_text).get("source_revision")
        en_revision = front_matter(en_text).get("source_revision")
        if zh_revision is not None and en_revision is not None and zh_revision != en_revision:
            errors.append(f"stale translation: {chapter_id}: zh={zh_revision}, en={en_revision}")
    return errors


def main():
    errors = validate()
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        return 1
    count = len(list((ROOT / "docs" / "zh").glob("*.md")))
    print(f"parity ok: {count} bilingual chapter(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
