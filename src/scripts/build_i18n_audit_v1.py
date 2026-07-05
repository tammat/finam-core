from __future__ import annotations

import re
from pathlib import Path

PAGES = [
    "strategy_platform.py",
    "strategy_governance.py",
    "edge_platform.py",
    "risk_platform.py",
    "trading_platform.py",
    "portfolio_platform.py",
]

ROOT = Path("src/marketcore/presentation/pages")
LABELS = Path("src/marketcore/presentation/ui_labels.py")

label_text = LABELS.read_text(encoding="utf-8")
defined = set(re.findall(r'"([^"]+)"\s*:', label_text))

used: set[str] = set()

for name in PAGES:
    path = ROOT / name
    if not path.exists():
        raise SystemExit(f"MISSING_PAGE {path}")

    text = path.read_text(encoding="utf-8")
    used.update(re.findall(r'display_label\("([^"]+)"\)', text))
    used.update(re.findall(r'_label\("([^"]+)"\)', text))

missing = sorted(k for k in used if k not in defined)

print("=== I18N_AUDIT_V1 ===")
print(f"platform_pages={len(PAGES)}")
print(f"used_labels={len(used)}")
print(f"defined_labels={len(defined)}")
print(f"missing_labels={len(missing)}")

for k in missing:
    print(f"MISSING_LABEL {k}")

if missing:
    print("VERDICT=I18N_AUDIT_V1_FAILED")
    raise SystemExit(1)

print("VERDICT=I18N_AUDIT_V1_OK")
