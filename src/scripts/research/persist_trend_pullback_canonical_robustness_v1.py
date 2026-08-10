from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path

import psycopg2


OUT_PATH = Path(
    "/tmp/trend_pullback_canonical_robustness_v1.out"
)

ROW_RE = re.compile(
    r"^SYMBOL_ROBUSTNESS_ROW "
    r"symbol=(?P<symbol>\S+) "
    r"positive_variants=(?P<positive>\d+)/(?P<variants>\d+) "
    r"fold_stable_variants=(?P<fold_positive>\d+)/(?P<fold_total>\d+) "
    r"positive_ratio=(?P<positive_ratio>[0-9.]+) "
    r"fold_stable_ratio=(?P<fold_ratio>[0-9.]+) "
    r"robust=(?P<robust>[01])$"
)


def parse_rows(text: str) -> list[dict]:
    rows = []

    for line in text.splitlines():
        match = ROW_RE.match(line.strip())

        if not match:
            continue

        data = match.groupdict()

        rows.append(
            {
                "symbol": data["symbol"],
                "positive_variants": int(data["positive"]),
                "variants_total": int(data["variants"]),
                "fold_stable_variants": int(data["fold_positive"]),
                "fold_count": int(data["fold_total"]),
                "positive_neighbor_ratio": data["positive_ratio"],
                "fold_stable_ratio": data["fold_ratio"],
                "robust": data["robust"] == "1",
            }
        )

    return rows


def main() -> int:
    if not OUT_PATH.exists():
        raise SystemExit(
            f"ERROR=ROBUSTNESS_OUTPUT_NOT_FOUND path={OUT_PATH}"
        )

    text = OUT_PATH.read_text()

    if (
        "VERDICT="
        "TREND_PULLBACK_CANONICAL_ROBUSTNESS_SURVIVORS_CONFIRMED"
        not in text
    ):
        raise SystemExit(
            "ERROR=ROBUSTNESS_FINAL_VERDICT_NOT_CONFIRMED"
        )

    rows = parse_rows(text)

    if len(rows) != 3:
        raise SystemExit(
            f"ERROR=UNEXPECTED_SYMBOL_ROW_COUNT rows={len(rows)}"
        )

    output_hash = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    run_uuid = uuid.uuid5(
        uuid.NAMESPACE_URL,
        "marketcore:"
        "TREND_PULLBACK_CANONICAL_ROBUSTNESS_V1:"
        + output_hash,
    )

    dsn = os.environ.get("DATABASE_URL")

    if not dsn:
        raise SystemExit(
            "ERROR=DATABASE_URL_NOT_SET"
        )

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            for row in rows:
                status = (
                    "ROBUST"
                    if row["robust"]
                    else "FAIL"
                )

                cur.execute(
                    """
                    INSERT INTO
                    analytics.trend_pullback_canonical_robustness_v1
                    (
                        run_uuid,
                        symbol,
                        strategy_code,
                        timeframe,
                        variants_total,
                        positive_variants,
                        positive_neighbor_ratio,
                        stable_variants,
                        variants_evaluated_for_fold_stability,
                        fold_stable_ratio,
                        robustness_status,
                        robust,
                        execution_costs_used,
                        economic_edge_claimed,
                        runtime_changed,
                        execution_changed,
                        orders_changed,
                        fills_changed,
                        micro_live_allowed
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        'TREND_PULLBACK_V1',
                        'M5',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        false,
                        false,
                        false,
                        false,
                        false,
                        false,
                        false
                    )
                    ON CONFLICT (run_uuid, symbol)
                    DO NOTHING
                    """,
                    (
                        str(run_uuid),
                        row["symbol"],
                        row["variants_total"],
                        row["positive_variants"],
                        row["positive_neighbor_ratio"],
                        row["fold_stable_variants"],
                        row["fold_count"],
                        row["fold_stable_ratio"],
                        status,
                        row["robust"],
                    ),
                )

    print(f"run_uuid={run_uuid}")
    print(f"rows_inserted={len(rows)}")
    print("execution_costs_used=0")
    print("economic_edge_claimed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "TREND_PULLBACK_CANONICAL_ROBUSTNESS_PERSISTED_V1"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
