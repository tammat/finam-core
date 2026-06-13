#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"

if [[ ! -x "$PY_BIN" ]]; then
  PY_BIN="$(command -v python3)"
fi

echo "TEST_ACCUMULATION_SUMMARY_RU_V1_START"

"$PY_BIN" -m py_compile src/scripts/observability/build_accumulation_summary_ru_v1.py

"$PY_BIN" src/scripts/observability/build_accumulation_summary_ru_v1.py > /tmp/accumulation_summary_ru_v1.out

grep -q "СВОДКА НАКОПЛЕНИЯ СТАТИСТИКИ" /tmp/accumulation_summary_ru_v1.out
grep -q "ФОКУС ПО СЫРЬЮ И ВАЛЮТЕ" /tmp/accumulation_summary_ru_v1.out
grep -q "ИТОГО" /tmp/accumulation_summary_ru_v1.out

echo "TEST_ACCUMULATION_SUMMARY_RU_V1_OK"
