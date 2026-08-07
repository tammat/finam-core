#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
BUILDER="scripts/research/build_finam_futures_csv_import_v1.py"

FIXTURE="/tmp/finam_futures_csv_import_v1_fixture.csv"
LOG="/tmp/test_finam_futures_csv_import_v1.log"

cd "$ROOT"

cat > "$FIXTURE" <<'CSV'
Дата;Время;Операция;Полное наименование операции;Краткое наименование ценной бумаги;Тикер;Идентификатор счета;Объем транзакции;Валюта;Количество;Цена за штуку;Комментарий
2026-05-11;09:00:01;Покупка производного финансового инструмента;;BR-6.26;BRM6;TEST_ACCOUNT;;пт.;1.0;105,64;
2026-05-11;11:05:18;Продажа производного финансового инструмента;;BR-6.26;BRM6;TEST_ACCOUNT;;пт.;1.0;104,73;
CSV

PYTHONPATH=src \
"$PYTHON" -m py_compile "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --input "$FIXTURE" |
tee "$LOG"

grep -Fq "futures_fill_count=2" "$LOG"
grep -Fq "verified_fill_count=2" "$LOG"
grep -Fq "unresolved_count=0" "$LOG"
grep -Fq \
  "VERDICT=FINAM_FUTURES_CSV_IMPORT_V1_DRY_RUN_OK" \
  "$LOG"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_FINAM_FUTURES_CSV_IMPORT_V1_OK"
