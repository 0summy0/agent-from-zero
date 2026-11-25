import tomllib, sys
from packaging.requirements import Requirement

data = tomllib.load(open("pyproject.toml", "rb"))
specs = list(data.get("project", {}).get("dependencies", []))
for g in data.get("dependency-groups", {}).values():
    specs += [s for s in g if isinstance(s, str)]

bad = []
for s in specs:
    r = Requirement(s)
    if not any(sp.operator in ("<", "<=", "==", "~=") for sp in r.specifier):
        bad.append(s)
print(f"{len(specs)} deps checked, {len(bad)} unbounded")
for b in bad:
    print("  FAIL:", b)
sys.exit(1 if bad else 0)
