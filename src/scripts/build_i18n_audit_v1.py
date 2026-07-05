from __future__ import annotations

import ast
import re
from pathlib import Path

from marketcore.presentation.registry import menu_pages

ROOT = Path("src/marketcore/presentation/pages")
LABELS = Path("src/marketcore/presentation/ui_labels.py")

label_text = LABELS.read_text(encoding="utf-8")
defined = set(re.findall(r'"([^"]+)"\s*:', label_text))

active_modules = {
    p.__class__.__module__.split(".")[-1]
    for p in menu_pages()
}

used: set[str] = set()
violations: list[str] = []

for module in sorted(active_modules):
    path = ROOT / f"{module}.py"
    if not path.exists():
        continue

    text = path.read_text(encoding="utf-8")

    used.update(re.findall(r'display_label\("([^"]+)"\)', text))
    used.update(re.findall(r'_label\("([^"]+)"\)', text))

    tree = ast.parse(text)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue

        s = node.value.strip()

        if not s:
            continue

        if s.startswith(("/", "api/", "http", "SELECT", "FROM")):
            continue

        if re.fullmatch(r"[A-Z0-9_./: -]+", s):
            continue

        if any(ch in s for ch in "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"):
            violations.append(f"{path}:{node.lineno}: hardcoded_ru_string={s[:120]}")

missing = sorted(k for k in used if k not in defined)

print("=== I18N_AUDIT_V1 ===")
print(f"active_pages={len(active_modules)}")
print(f"used_labels={len(used)}")
print(f"defined_labels={len(defined)}")
print(f"missing_labels={len(missing)}")
print(f"hardcoded_ru_strings={len(violations)}")

for k in missing[:200]:
    print(f"MISSING_LABEL {k}")

for v in violations[:200]:
    print(f"HARDCODED_STRING {v}")

if missing or violations:
    print("VERDICT=I18N_AUDIT_V1_FAILED")
    raise SystemExit(1)

print("VERDICT=I18N_AUDIT_V1_OK")
