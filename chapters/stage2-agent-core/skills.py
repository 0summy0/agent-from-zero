import json
import tempfile
from pathlib import Path

CHAPTER_ID = "2.6-agent-skills"


def parse_scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_skill(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing opening front-matter delimiter")
    try:
        closing = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        raise ValueError(f"{path}: missing closing front-matter delimiter") from None

    metadata = {}
    for line in lines[1:closing]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}: expected a front-matter key/value pair")
        key, value = line.split(":", 1)
        key = key.strip()
        if key in metadata:
            raise ValueError(f"{path}: duplicate front-matter key {key!r}")
        metadata[key] = parse_scalar(value)

    for key in ("name", "description"):
        if not metadata.get(key):
            raise ValueError(f"{path}: front matter requires a non-empty {key}")
    return {
        "name": metadata["name"],
        "description": metadata["description"],
        "instructions": "\n".join(lines[closing + 1 :]).strip(),
    }


class SkillLibrary:
    def __init__(self, root):
        self.root = Path(root)
        self.skills_dir = self.root / "skills"

    def _skill_paths(self):
        return sorted(self.skills_dir.glob("*/SKILL.md"), key=lambda path: path.parent.name)

    def list_skills(self):
        skills = []
        names = set()
        for path in self._skill_paths():
            skill = parse_skill(path)
            if skill["name"] in names:
                raise ValueError(f"duplicate skill name: {skill['name']}")
            names.add(skill["name"])
            skills.append({"name": skill["name"], "description": skill["description"]})
        return sorted(skills, key=lambda skill: skill["name"])

    def load_skill(self, name):
        for path in self._skill_paths():
            skill = parse_skill(path)
            if skill["name"] == name:
                return skill
        raise KeyError(f"skill not found: {name}")

    def render_skill_prompt(self, skill):
        if not isinstance(skill, dict):
            raise TypeError("render_skill_prompt expects a loaded skill dictionary")
        missing = {"name", "description", "instructions"} - skill.keys()
        if missing:
            raise ValueError(f"loaded skill is missing fields: {sorted(missing)}")
        return (
            f"## Skill: {skill['name']}\n\n"
            f"Description: {skill['description']}\n\n"
            f"Instructions:\n{skill['instructions']}"
        )


def write_skill(root, directory_name, name, description, instructions):
    path = Path(root) / "skills" / directory_name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "---\n"
        f"name: {name}\n"
        f'description: "{description}"\n'
        "---\n\n"
        f"{instructions}\n",
        encoding="utf-8",
    )


def run_minimal_path():
    with tempfile.TemporaryDirectory(prefix="agent-skills-") as temporary_root:
        root = Path(temporary_root)
        write_skill(
            root,
            "summarize",
            "summarize",
            "Condense a passage into three factual bullet points.",
            "Read the passage. Preserve named entities and numbers. Return exactly three bullets.",
        )
        write_skill(
            root,
            "translate",
            "translate",
            "Translate short English text into Chinese.",
            "Translate the input without adding commentary. Preserve product names.",
        )
        library = SkillLibrary(root)
        discovered = library.list_skills()
        loaded = library.load_skill("summarize")
        prompt = library.render_skill_prompt(loaded)
    return {
        "chapter": CHAPTER_ID,
        "discovered_skills": discovered,
        "skill_name": loaded["name"],
        "description": loaded["description"],
        "instructions": loaded["instructions"],
        "prompt": prompt,
    }


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
