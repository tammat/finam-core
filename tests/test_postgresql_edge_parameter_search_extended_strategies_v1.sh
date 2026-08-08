#!/usr/bin/env bash
set -euo pipefail

BUILDER="scripts/research/build_postgresql_edge_parameter_search_v1.py"

DEFAULT_BATCH="TEST_EDGE_SEARCH_DEFAULT_STRATEGIES_V1"
EXT_BATCH="TEST_EDGE_SEARCH_EXTENDED_STRATEGIES_V1"

DEFAULT_OUT="/tmp/postgresql_edge_parameter_search_v1/$DEFAULT_BATCH"
EXT_OUT="/tmp/postgresql_edge_parameter_search_v1/$EXT_BATCH"

echo "=== TEST_POSTGRESQL_EDGE_PARAMETER_SEARCH_EXTENDED_STRATEGIES_V1 ==="

PYTHONPATH=src python -m py_compile "$BUILDER"

rm -rf "$DEFAULT_OUT" "$EXT_OUT"

echo "=== DEFAULT COMPATIBILITY ==="

PYTHONPATH=src python "$BUILDER" \
  --symbols "BRU6@RTSX" \
  --timeframes "M5" \
  --commission-per-side 1.5 \
  --slippage-bps 2.0 \
  --bar-limit 20000 \
  --batch-id "$DEFAULT_BATCH" \
  --plan-only

python - "$DEFAULT_OUT/search_plan.tsv" <<'PY'
import csv
import sys
from collections import Counter

with open(
    sys.argv[1],
    encoding="utf-8",
    newline="",
) as stream:
    rows = list(
        csv.DictReader(stream, delimiter="\t")
    )

counts = Counter(
    row["strategy_code"]
    for row in rows
)

assert len(rows) == 36

assert counts == {
    "ATR_IMPULSE_V1": 24,
    "MOMENTUM_CONTINUATION_V1": 12,
}

print("default_task_count=36")
print("default_behavior_preserved=1")
PY

echo "=== EXTENDED EXPLICIT MODE ==="

PYTHONPATH=src python "$BUILDER" \
  --symbols "BRU6@RTSX,BRV6@RTSX,NGQ6@RTSX,NGU6@RTSX" \
  --timeframes "M5" \
  --strategies \
    MEAN_REVERSION_ZSCORE_V1 \
    TREND_PULLBACK_V1 \
    VOLATILITY_BREAKOUT_FILTERED_V1 \
  --commission-per-side 1.5 \
  --slippage-bps 2.0 \
  --bar-limit 20000 \
  --batch-id "$EXT_BATCH" \
  --plan-only

python - "$EXT_OUT/search_plan.tsv" <<'PY'
import csv
import json
import sys
from collections import Counter
from decimal import Decimal

with open(
    sys.argv[1],
    encoding="utf-8",
    newline="",
) as stream:
    rows = list(
        csv.DictReader(stream, delimiter="\t")
    )

assert len(rows) == 240

strategy_counts = Counter(
    row["strategy_code"]
    for row in rows
)

symbol_counts = Counter(
    row["symbol"]
    for row in rows
)

hashes = {
    row["parameter_hash"]
    for row in rows
}

assert strategy_counts == {
    "MEAN_REVERSION_ZSCORE_V1": 72,
    "TREND_PULLBACK_V1": 96,
    "VOLATILITY_BREAKOUT_FILTERED_V1": 72,
}

assert symbol_counts == {
    "BRU6@RTSX": 60,
    "BRV6@RTSX": 60,
    "NGQ6@RTSX": 60,
    "NGU6@RTSX": 60,
}

assert len(hashes) == 240

for row in rows:
    p = json.loads(row["parameter_json"])

    assert (
        p["commission_model"]
        == "FINAM_FUTURES_CONFIGURED_V1"
    )

    assert Decimal(
        str(
            p[
                "futures_broker_fee_per_contract_per_side"
            ]
        )
    ) == Decimal("0.45")

    assert Decimal(
        str(p["commission_per_side"])
    ) == Decimal("0")

    assert (
        p["futures_fee_evidence_verified"]
        is True
    )

print("extended_task_count=240")
print("unique_parameter_hashes=240")
print("mean_reversion_tasks=72")
print("trend_pullback_tasks=96")
print("volatility_breakout_tasks=72")
print("atr_tasks=0")
print("momentum_tasks=0")
print("verified_futures_cost_contract_preserved=1")
PY

echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_POSTGRESQL_EDGE_PARAMETER_SEARCH_EXTENDED_STRATEGIES_V1_OK"
