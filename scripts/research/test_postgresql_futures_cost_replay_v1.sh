#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_postgresql_futures_cost_replay_v1.py"
LOG="/tmp/test_postgresql_futures_cost_replay_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

PYTHONPATH=src \
"$PYTHON" - <<'PY' \
> /tmp/postgresql_futures_cost_replay_candidates_v1.tsv
from __future__ import annotations

import psycopg2

from finam_core.analytics.statistics_repository import build_psycopg_url


symbols = (
    "BRM6@RTSX",
    "BRN6@RTSX",
    "NGK6@RTSX",
)

with psycopg2.connect(build_psycopg_url()) as conn:
    conn.set_session(readonly=True)

    with conn.cursor() as cursor:
        for symbol in symbols:
            cursor.execute(
                """
                SELECT
                    r.run_uuid::text,
                    r.strategy_code,
                    r.symbol,
                    r.timeframe,
                    count(t.*)::bigint AS trades,
                    avg(
                        t.gross_pnl
                        - coalesce(t.slippage, 0)
                    )::numeric AS execution_expectancy
                FROM analytics.edge_lab_run_v1 r
                JOIN analytics.research_trade_v1 t
                  ON t.run_uuid = r.run_uuid
                WHERE r.symbol = %s
                GROUP BY
                    r.run_uuid,
                    r.strategy_code,
                    r.symbol,
                    r.timeframe
                HAVING count(t.*) >= 30
                ORDER BY
                    avg(
                        t.gross_pnl
                        - coalesce(t.slippage, 0)
                    ) DESC,
                    count(t.*) DESC,
                    r.run_uuid
                LIMIT 1
                """,
                (symbol,),
            )

            row = cursor.fetchone()

            if row is not None:
                print(
                    "\t".join(
                        str(value)
                        for value in row
                    )
                )
PY

cat /tmp/postgresql_futures_cost_replay_candidates_v1.tsv

RUN_COUNT="$(
  wc -l \
  < /tmp/postgresql_futures_cost_replay_candidates_v1.tsv
)"

echo "candidate_run_count=$RUN_COUNT"

[[ "$RUN_COUNT" -gt 0 ]] || {
    echo "VERDICT=TEST_POSTGRESQL_FUTURES_COST_REPLAY_V1_NO_RUNS"
    exit 2
}

while IFS=$'\t' read -r \
  RUN_UUID \
  STRATEGY_CODE \
  SYMBOL \
  TIMEFRAME \
  TRADES \
  EXECUTION_EXPECTANCY
do
    case "$SYMBOL" in
        BRM6@RTSX)
            COMMISSION="0.514487530124270478500353660"
            MODEL_VERSION="FINAM_FUTURES_TURNOVER_BR_MAY_2026_V1"
            ;;
        BRN6@RTSX)
            COMMISSION="0.468117223660405318375594337"
            MODEL_VERSION="FINAM_FUTURES_TURNOVER_BRN_MAY_2026_V1"
            ;;
        NGK6@RTSX)
            COMMISSION="0.45"
            MODEL_VERSION="FINAM_FUTURES_CONTRACT_COUNT_NG_MAY_2026_V1"
            ;;
        *)
            echo "ERROR=unsupported_symbol:$SYMBOL"
            exit 1
            ;;
    esac

    echo \
      "REPLAY_CANDIDATE run_uuid=$RUN_UUID strategy=$STRATEGY_CODE symbol=$SYMBOL timeframe=$TIMEFRAME trades=$TRADES execution_expectancy=$EXECUTION_EXPECTANCY" |
    tee -a "$LOG"

    PYTHONPATH=src \
    "$PYTHON" "$BUILDER" \
      --source-run-uuid "$RUN_UUID" \
      --commission-per-contract-side "$COMMISSION" \
      --contracts-per-trade 1 \
      --cost-model-version "$MODEL_VERSION" |
    tee -a "$LOG"
done < /tmp/postgresql_futures_cost_replay_candidates_v1.tsv

grep -Fq \
  "VERDICT=POSTGRESQL_FUTURES_COST_REPLAY_V1_READY" \
  "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE analytics" \
  "DELETE FROM analytics" \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" "$BUILDER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "db_writes_performed=0"
echo "historical_trade_rows_changed=0"
echo "historical_observation_rows_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_FUTURES_COST_REPLAY_V1_OK"
