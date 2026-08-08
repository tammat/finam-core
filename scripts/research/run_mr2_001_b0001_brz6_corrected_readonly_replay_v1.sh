#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

BATCH_ID="MR2_001_B0001_MOMENTUM_M5"
SYMBOL="BRZ6@RTSX"
STRATEGY="MOMENTUM_CONTINUATION_V1"
TIMEFRAME="M5"

OUT_DIR="/tmp/mr2_001_b0001_brz6_corrected_readonly_v1"
RUN_DIR="$OUT_DIR/runs"
RANKING="$OUT_DIR/ranking.tsv"
RUN_LIST="$OUT_DIR/run_list.tsv"

rm -rf "$OUT_DIR"
mkdir -p "$RUN_DIR"

echo "=== MR2-001 B0001 BRZ6 CORRECTED READONLY REPLAY V1 ==="

PYTHONPATH=src \
/opt/finam-core/venv/bin/python - <<'PY' > "$RUN_LIST"
import psycopg2

from finam_core.analytics.statistics_repository import build_psycopg_url

BATCH = "MR2_001_B0001_MOMENTUM_M5"

with psycopg2.connect(build_psycopg_url()) as conn:
    conn.set_session(readonly=True)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                run_uuid::text,
                parameter_hash
            FROM analytics.edge_lab_run_v1
            WHERE research_batch_id=%s
              AND strategy_code='MOMENTUM_CONTINUATION_V1'
              AND symbol='BRZ6@RTSX'
              AND timeframe='M5'
              AND status_code='DONE'
            ORDER BY parameter_hash
            """,
            (BATCH,),
        )

        rows = cur.fetchall()

if len(rows) != 12:
    raise SystemExit(
        "ERROR=BRZ6_FROZEN_RUN_COUNT_MISMATCH:"
        f"actual={len(rows)}"
    )

if len({row[1] for row in rows}) != 12:
    raise SystemExit(
        "ERROR=BRZ6_PARAMETER_HASH_NOT_UNIQUE"
    )

for run_uuid, parameter_hash in rows:
    print(f"{run_uuid}\t{parameter_hash}")
PY

RUN_COUNT="$(wc -l < "$RUN_LIST" | tr -d ' ')"
test "$RUN_COUNT" -eq 12

echo "frozen_run_count=$RUN_COUNT"

while IFS=$'\t' read -r RUN_UUID PARAMETER_HASH
do
    LOG="$RUN_DIR/${PARAMETER_HASH}.log"

    echo \
      "REPLAY_START run_uuid=$RUN_UUID parameter_hash=$PARAMETER_HASH"

    PYTHONPATH=src \
    /opt/finam-core/venv/bin/python \
      src/finam_core/research/postgresql_edge_backtest_adapter_v1.py \
      --run-uuid "$RUN_UUID" \
      --dry-run \
      > "$LOG"

    grep -Fq \
      "VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_DRY_RUN_OK" \
      "$LOG"

    grep -Fq "symbol=$SYMBOL" "$LOG"
    grep -Fq "db_writes_performed=0" "$LOG"

    echo \
      "REPLAY_DONE run_uuid=$RUN_UUID parameter_hash=$PARAMETER_HASH"
done < "$RUN_LIST"

PYTHONPATH=src \
/opt/finam-core/venv/bin/python - <<'PY'
from decimal import Decimal
from pathlib import Path

root = Path(
    "/tmp/mr2_001_b0001_brz6_corrected_readonly_v1"
)

run_list = root / "run_list.tsv"
run_dir = root / "runs"
ranking = root / "ranking.tsv"

rows = []

for line in run_list.read_text(
    encoding="utf-8"
).splitlines():
    run_uuid, parameter_hash = line.split("\t")

    values = {}

    for raw in (
        run_dir / f"{parameter_hash}.log"
    ).read_text(
        encoding="utf-8"
    ).splitlines():
        if "=" not in raw:
            continue

        key, value = raw.split("=", 1)
        values[key] = value

    required = (
        "trades",
        "expectancy",
        "profit_factor",
        "market_pnl_sum",
        "gross_pnl_sum",
        "commission_sum",
        "slippage_sum",
        "net_pnl_sum",
        "gross_identity_error",
        "net_identity_error",
        "verdict_code",
    )

    missing = [
        key
        for key in required
        if key not in values
    ]

    if missing:
        raise SystemExit(
            "ERROR=CORRECTED_RUN_FIELDS_MISSING:"
            f"hash={parameter_hash}:"
            f"fields={','.join(missing)}"
        )

    if Decimal(
        values["gross_identity_error"]
    ) != 0:
        raise SystemExit(
            "ERROR=GROSS_IDENTITY_MISMATCH:"
            f"hash={parameter_hash}"
        )

    if Decimal(
        values["net_identity_error"]
    ) != 0:
        raise SystemExit(
            "ERROR=NET_IDENTITY_MISMATCH:"
            f"hash={parameter_hash}"
        )

    rows.append(
        {
            "run_uuid": run_uuid,
            "parameter_hash": parameter_hash,
            "trades": int(values["trades"]),
            "market_pnl_sum": Decimal(
                values["market_pnl_sum"]
            ),
            "gross_pnl_sum": Decimal(
                values["gross_pnl_sum"]
            ),
            "slippage_sum": Decimal(
                values["slippage_sum"]
            ),
            "commission_sum": Decimal(
                values["commission_sum"]
            ),
            "net_pnl_sum": Decimal(
                values["net_pnl_sum"]
            ),
            "expectancy": Decimal(
                values["expectancy"]
            ),
            "profit_factor": Decimal(
                values["profit_factor"]
            ),
            "verdict_code": values["verdict_code"],
        }
    )

rows.sort(
    key=lambda row: (
        row["net_pnl_sum"],
        row["expectancy"],
        row["profit_factor"],
    ),
    reverse=True,
)

header = (
    "rank\trun_uuid\tparameter_hash\ttrades\t"
    "market_pnl_sum\tgross_pnl_sum\t"
    "slippage_sum\tcommission_sum\t"
    "net_pnl_sum\texpectancy\t"
    "profit_factor\tverdict_code"
)

output = [header]

for rank, row in enumerate(rows, 1):
    output.append(
        "\t".join(
            (
                str(rank),
                row["run_uuid"],
                row["parameter_hash"],
                str(row["trades"]),
                str(row["market_pnl_sum"]),
                str(row["gross_pnl_sum"]),
                str(row["slippage_sum"]),
                str(row["commission_sum"]),
                str(row["net_pnl_sum"]),
                str(row["expectancy"]),
                str(row["profit_factor"]),
                row["verdict_code"],
            )
        )
    )

ranking.write_text(
    "\n".join(output) + "\n",
    encoding="utf-8",
)

print(f"corrected_run_count={len(rows)}")
print(
    "positive_market_run_count="
    f"{sum(r['market_pnl_sum'] > 0 for r in rows)}"
)
print(
    "positive_gross_run_count="
    f"{sum(r['gross_pnl_sum'] > 0 for r in rows)}"
)
print(
    "positive_net_run_count="
    f"{sum(r['net_pnl_sum'] > 0 for r in rows)}"
)

for rank, row in enumerate(rows, 1):
    print(
        "CORRECTED_RANK "
        f"rank={rank} "
        f"parameter_hash={row['parameter_hash']} "
        f"trades={row['trades']} "
        f"market_pnl_sum={row['market_pnl_sum']} "
        f"gross_pnl_sum={row['gross_pnl_sum']} "
        f"slippage_sum={row['slippage_sum']} "
        f"commission_sum={row['commission_sum']} "
        f"net_pnl_sum={row['net_pnl_sum']} "
        f"expectancy={row['expectancy']} "
        f"profit_factor={row['profit_factor']} "
        f"verdict_code={row['verdict_code']}"
    )

print(f"ranking_file={ranking}")
PY

echo "db_writes_performed=0"
echo "original_batch_mutated=0"

echo "parameter_grid_changed=0"
echo "new_parameter_search_performed=0"

echo "ngk6_corrected_replay_allowed=0"
echo "generic_ng_fallback_allowed=0"

echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"

echo \
  "VERDICT=MR2_001_B0001_BRZ6_CORRECTED_READONLY_REPLAY_V1_READY"
