#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_moex_liquid_universe.sql >/dev/null

python -m py_compile src/scripts/update_moex_liquid_universe.py

PYTHONPATH=src python src/scripts/update_moex_liquid_universe.py

psql "$DATABASE_URL" -P pager=off -c "
select symbol, asset_class, board, group_name, enabled
from moex_liquid_universe
where enabled = true
order by group_name, symbol;
"

echo "OK: moex liquid universe"
