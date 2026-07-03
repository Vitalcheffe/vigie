"""Clean AI planning markers from Vigie source files."""
import re
from pathlib import Path

PATTERNS = [
    (r"Stub:", "TODO:"),
    (r"\s*in J\d+(?:-J\d+)?\b", ""),
    (r"\s*en J\d+(?:-J\d+)?\b", ""),
    (r"\(J\d+(?:-J\d+)?\)\s*", ""),
    (r"\(fonctionnalité J\d+\)", "(à venir)"),
    (r"\(implémentation en J\d+\)", "(à venir)"),
    (r"\(Implémentation complète en J\d+(?:-J\d+)?\.\)", "(implémentation à venir.)"),
    (r"données temps réel disponibles en J\d+ \(dashboard\)", "données temps réel à venir"),
    (r"génération à venir en J\d+", "génération à venir"),
    (r"Reset demandé — implémentation en J\d+", "Reset demandé — à venir"),
    (r"Le tableau de bord temps réel sera disponible en J\d+", "Le tableau de bord temps réel sera disponible prochainement"),
    (r"# Sub-command implementations \(stubs for J\d+, fleshed out later\)", "# Sub-command implementations"),
    (r"stubs for J\d+", "stubs"),
    (r"fleshed out later", "completed as needed"),
]

base = Path("/home/z/my-project/vigie")
files = list(base.rglob("*.py")) + list(base.rglob("*.md")) + list(base.rglob("*.yaml")) + list(base.rglob("*.toml"))
files = [f for f in files if ".git" not in f.parts]

changed = 0
for f in files:
    text = f.read_text(encoding="utf-8")
    original = text
    for pat, repl in PATTERNS:
        text = re.sub(pat, repl, text)
    if text != original:
        f.write_text(text, encoding="utf-8")
        changed += 1
        print(f"  cleaned: {f.relative_to(base)}")

print(f"\nTotal files cleaned: {changed}")
