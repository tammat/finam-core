#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
FILE="scripts/research/build_postgresql_edge_parameter_search_v1.py"

cd "$ROOT"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$FILE"

grep -Fq 'reason=NO_BARS' "$FILE"
grep -Fq 'reason=INSUFFICIENT_BARS' "$FILE"
grep -Fq 'FROM public.market_bars' "$FILE"
grep -Fq 'task.parameters.get("minimum_bars", 100)' "$FILE"

PYTHONPATH=src \
"$PYTHON" - <<'PY'
from __future__ import annotations

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


cases = (
    ("SBER@MISX", "M5"),
    ("LKOH@MISX", "M5"),
    ("NG@RTSX", "M5"),
)

with psycopg2.connect(build_psycopg_url()) as conn:
    conn.set_session(readonly=True)

    with conn.cursor(
        cursor_factory=RealDictCursor,
    ) as cur:
        for symbol, timeframe in cases:
            cur.execute(
                """
                SELECT count(*)::bigint AS bar_count
                FROM public.market_bars
                WHERE symbol = %s
                  AND timeframe = %s
                """,
                (symbol, timeframe),
            )

            bars = int(
                cur.fetchone()["bar_count"] or 0
            )

            status = (
                "NO_BARS"
                if bars == 0
                else "BARS_PRESENT"
            )

            print(
                "BAR_PREFLIGHT "
                f"symbol={symbol} "
                f"timeframe={timeframe} "
                f"bars={bars} "
                f"status={status}"
            )

print("db_writes_performed=0")
print(
    "VERDICT="
    "POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_BARS_RUNTIME_OK"
)
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_POSTGRESQL_EDGE_PARAMETER_SEARCH_PREFLIGHT_BARS_V1_OK"
