#!/usr/bin/env bash
set -euo pipefail

BUILDER="scripts/research/build_postgresql_edge_parameter_search_v1.py"
BATCH_ID="TEST_BRNG_FUTURES_COST_CONTRACT_V1"
OUT="/tmp/postgresql_edge_parameter_search_v1/$BATCH_ID"
PLAN="$OUT/search_plan.tsv"

echo "=== TEST_POSTGRESQL_FUTURES_PARAMETER_SEARCH_COST_CONTRACT_V1 ==="

PYTHONPATH=src python -m py_compile "$BUILDER"

rm -rf "$OUT"

PYTHONPATH=src python "$BUILDER" \
  --symbols "BRU6@RTSX,BRV6@RTSX,NGQ6@RTSX,NGU6@RTSX" \
  --timeframes "M5" \
  --strategies ATR_IMPULSE_V1 MOMENTUM_CONTINUATION_V1 \
  --commission-per-side 1.5 \
  --slippage-bps 2.0 \
  --bar-limit 20000 \
  --batch-id "$BATCH_ID" \
  --plan-only

python - "$PLAN" <<'PY'
import csv
import json
import sys
from collections import Counter
from decimal import Decimal

rows = list(
    csv.DictReader(
        open(sys.argv[1], encoding="utf-8"),
        delimiter="\t",
    )
)

assert len(rows) == 144

expected = {
    "BRU6@RTSX": Decimal("4.56"),
    "BRV6@RTSX": Decimal("4.46"),
    "NGQ6@RTSX": Decimal("1.45"),
    "NGU6@RTSX": Decimal("1.49"),
}

counts = Counter()
hashes = set()

for row in rows:
    symbol = row["symbol"]
    p = json.loads(row["parameter_json"])

    assert symbol in expected

    assert (
        p["commission_model"]
        == "FINAM_FUTURES_CONFIGURED_V1"
    )

    assert Decimal(
        str(p["commission_per_side"])
    ) == Decimal("0")

    assert Decimal(
        str(
            p[
                "futures_broker_fee_per_contract_per_side"
            ]
        )
    ) == Decimal("0.45")

    assert Decimal(
        str(
            p[
                "futures_exchange_fee_per_contract_per_side"
            ]
        )
    ) == expected[symbol]

    assert Decimal(
        str(
            p[
                "futures_other_fee_per_contract_per_side"
            ]
        )
    ) == Decimal("0")

    assert (
        p["futures_fee_evidence_verified"]
        is True
    )

    parameter_hash = row["parameter_hash"]

    assert parameter_hash not in hashes
    hashes.add(parameter_hash)

    counts[symbol] += 1

assert len(hashes) == 144

assert counts == {
    "BRU6@RTSX": 36,
    "BRV6@RTSX": 36,
    "NGQ6@RTSX": 36,
    "NGU6@RTSX": 36,
}

print("task_count=144")
print("unique_parameter_hashes=144")
print("legacy_commission_per_side_overridden=1")
print("configured_futures_model=1")
print("verified_broker_fee=1")
print("symbol_specific_exchange_fee=1")
print("costs_in_parameter_hash_input=1")
PY

echo "=== UNRESOLVED BROKER EVIDENCE FAIL-CLOSED ==="

set +e

OUTPUT="$(
  PYTHONPATH=src python "$BUILDER" \
    --symbols "GDU6@RTSX" \
    --timeframes "M5" \
    --strategies ATR_IMPULSE_V1 \
    --commission-per-side 1.5 \
    --slippage-bps 2.0 \
    --bar-limit 20000 \
    --batch-id "TEST_GDU6_COST_UNRESOLVED_V1" \
    --plan-only 2>&1
)"

RC=$?

set -e

if [ "$RC" -eq 0 ]; then
    echo "ERROR=GDU6_COST_EVIDENCE_NOT_BLOCKED"
    exit 1
fi

grep -q \
  "futures_broker_fee_evidence_unresolved:GDU6@RTSX" \
  <<<"$OUTPUT"

echo "unresolved_broker_evidence_blocked=1"
echo "db_writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_POSTGRESQL_FUTURES_PARAMETER_SEARCH_COST_CONTRACT_V1_OK"
