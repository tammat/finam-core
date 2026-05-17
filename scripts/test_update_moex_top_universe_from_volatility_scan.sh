#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_moex_top_universe.sql >/dev/null

python -m py_compile src/scripts/update_moex_top_universe_from_volatility_scan.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_moex_top_universe_from_volatility_scan.py").read_text(encoding="utf-8")

checks = [
    "volatility_scan_results",
    "moex_top_universe",
    "MOEX_TOP_UNIVERSE_LIMIT",
    "turnover_score",
    "volatility_score",
    "volume_score",
    "total_score",
]

for c in checks:
    assert c in text, c

print("OK: moex top universe updater static check")
PY

PYTHONPATH=src python src/scripts/update_moex_top_universe_from_volatility_scan.py

psql "$DATABASE_URL" -P pager=off -c "
select symbol, total_score, reason, calculated_at
from moex_top_universe
order by calculated_at desc, total_score desc
limit 30;
"

echo "OK: moex top universe updater"
