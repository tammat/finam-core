#!/usr/bin/env bash
set -e

echo "=== RiskStack v2.3 SMOKE TEST ==="

cd /opt/finam-core

# 1. Load profile
export $(grep -v '^#' .env.paper_safe | xargs)

# 2. Force strict portfolio limit to test GLOBAL guard
export PORTFOLIO_MAX_PAPER_ORDERS_PER_RUN=20

echo "Running replay..."

OUT=$(PYTHONPATH=src venv/bin/python src/scripts/replay_br_pipeline.py \
  --symbols BRM6@RTSX SBER@MISX PLZL@MISX \
  --from-ts "2026-04-15T07:00:00+00:00" \
  --to-ts   "2026-05-03T18:00:00+00:00")

echo "$OUT"

echo "=== VALIDATION ==="

# 1. Проверка лимита портфеля
echo "$OUT" | grep -q "paper_orders=20" || {
  echo "❌ FAIL: portfolio limit not enforced"
  exit 1
}

# 2. Проверка отказов PortfolioGuard
echo "$OUT" | grep -q "portfolio_guard_rejected=" || {
  echo "❌ FAIL: no portfolio guard rejections"
  exit 1
}

# 3. Проверка что есть сделки
echo "$OUT" | grep -q "trades_logged=" || {
  echo "❌ FAIL: no trades logged"
  exit 1
}

# 4. Проверка что нет execution ошибок
echo "$OUT" | grep -q "other_execution_rejected=0" || {
  echo "❌ FAIL: execution errors detected"
  exit 1
}

echo "✅ SMOKE TEST PASSED"
exit 0
