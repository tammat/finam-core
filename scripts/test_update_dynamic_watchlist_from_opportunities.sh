#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/alter_dynamic_watchlist_opportunity_fields.sql >/dev/null

python -m py_compile \
  src/scripts/update_dynamic_watchlist_from_opportunities.py \
  src/finam_core/data/postgres_opportunity_scanner.py \
  src/finam_core/data/moex_opportunity_scanner.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_dynamic_watchlist_from_opportunities.py").read_text(encoding="utf-8")

assert "PostgresOpportunityScanner" in text
assert "dynamic_watchlist" in text
assert "opportunity_scanner" in text
assert "json.dumps(raw" in text
assert "on conflict (symbol) do update" in text
assert "OPPORTUNITY_WATCHLIST" in text

print("OK: dynamic watchlist opportunity updater static check")
PY
