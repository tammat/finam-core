#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

MIGRATION="scripts/research/migrate_finam_futures_fill_evidence_v1.py"
BUILDER="scripts/research/build_finam_futures_fill_evidence_v1.py"
AUDIT="scripts/research/audit_finam_futures_fill_evidence_v1.py"

FIXTURE="/tmp/finam_futures_fill_evidence_v1_fixture.tsv"
LOG="/tmp/test_finam_futures_fill_evidence_v1.log"

cd "$ROOT"
rm -f "$FIXTURE" "$LOG"

cat > "$FIXTURE" <<'TSV'
execution_ts	trade_date	symbol	side	quantity_contracts	price	trade_id	order_id	broker_account	source_document	source_reference	source_version	evidence_status
2026-05-04T10:15:21+03:00	2026-05-04	BRM6@RTSX	BUY	2	61.45	TEST_BR_001	TEST_ORDER_001	TEST_ACCOUNT	TEST_ONLY	TEST_ROW_1	TEST_FUTURES_FILL_V1	VERIFIED
2026-05-04T10:20:00+03:00	2026-05-04	NGK6@RTSX	SELL	1	3.11	TEST_NG_001	TEST_ORDER_002	TEST_ACCOUNT	TEST_ONLY	TEST_ROW_2	TEST_FUTURES_FILL_V1	VERIFIED
TSV

PYTHONPATH=src \
"$PYTHON" -m py_compile \
  "$MIGRATION" \
  "$BUILDER" \
  "$AUDIT"

PYTHONPATH=src \
"$PYTHON" "$MIGRATION" --apply |
tee "$LOG"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --input "$FIXTURE" |
tee -a "$LOG"

PYTHONPATH=src \
"$PYTHON" "$AUDIT" |
tee -a "$LOG"

grep -Fq "valid_fill_count=2" "$LOG"
grep -Fq "verified_fill_count=2" "$LOG"
grep -Fq "review_required_count=0" "$LOG"
grep -Fq "unresolved_count=0" "$LOG"

grep -Fq \
  "VERDICT=FINAM_FUTURES_FILL_EVIDENCE_IMPORT_V1_DRY_RUN_OK" \
  "$LOG"

grep -Fq \
  "VERDICT=FINAM_FUTURES_FILL_EVIDENCE_V1_AUDIT_OK" \
  "$LOG"

for marker in \
  "UPDATE analytics.research_trade_v1" \
  "DELETE FROM analytics.research_trade_v1" \
  "UPDATE analytics.edge_observation_v1" \
  "DELETE FROM analytics.edge_observation_v1" \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" \
          "$MIGRATION" \
          "$BUILDER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "fixture_is_actual_evidence=0"
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
echo "VERDICT=TEST_FINAM_FUTURES_FILL_EVIDENCE_V1_OK"
