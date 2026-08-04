from __future__ import annotations

import argparse
import os
import uuid
from dataclasses import dataclass

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

# market_snapshot_v1 хранит volume с точностью до 4 знаков.
# Отличия в пределах половины минимального шага хранения
# считаются эквивалентными и не являются historical correction.
VOLUME_TOLERANCE = os.getenv(
    "FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE",
    "0.00005",
)
SOURCE_VERSION = "FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1"

DEFAULT_WINDOW_BARS = int(
    os.getenv(
        "FEATURE_STORE_CORRECTION_WINDOW_BARS",
        "200",
    )
)

MAX_WINDOW_BARS = int(
    os.getenv(
        "FEATURE_STORE_CORRECTION_MAX_WINDOW_BARS",
        "5000",
    )
)




@dataclass(frozen=True)
class AuditSummary:
    checked_pairs: int
    checked_rows: int
    changed_pairs: int
    changed_rows: int
    missing_market_snapshot_rows: int
    missing_market_bar_rows: int
    dirty_rows_updated: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Проверка поздних изменений исторических OHLCV "
            "между public.market_bars и "
            "marketcore.market_snapshot_v1."
        )
    )
    parser.add_argument(
        "--window-bars",
        type=int,
        default=DEFAULT_WINDOW_BARS,
        help=(
            "Количество последних market_bars для проверки "
            "по каждой паре symbol/timeframe."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Выполнить сравнение без записи аудита "
            "и без изменения dirty state."
        ),
    )
    parser.add_argument(
        "--symbol",
        default=None,
        help="Ограничить аудит одним symbol.",
    )
    parser.add_argument(
        "--timeframe",
        default=None,
        help="Ограничить аудит одним timeframe.",
    )
    return parser.parse_args()


def validate_window_bars(value: int) -> int:
    if value < 1:
        raise ValueError(
            "window-bars должен быть положительным числом"
        )

    if value > MAX_WINDOW_BARS:
        raise ValueError(
            "window-bars превышает безопасный предел "
            f"{MAX_WINDOW_BARS}"
        )

    return value


def ensure_contract(
    cur: psycopg2.extensions.cursor,
) -> None:
    cur.execute(
        """
        SELECT to_regclass(
            'analytics.'
            'feature_store_historical_correction_audit_v1'
        ) AS audit_table
        """
    )

    row = cur.fetchone()
    table_name = row["audit_table"] if row else None

    if table_name is None:
        raise RuntimeError(
            "Не применена migration "
            "sql/analytics/"
            "014_feature_store_historical_correction_audit_v1.sql"
        )



def audit_pairs(
    cur: psycopg2.extensions.cursor,
    *,
    audit_run_id: str,
    window_bars: int,
    dry_run: bool,
    symbol: str | None,
    timeframe: str | None,
) -> AuditSummary:
    cur.execute(
        """
        WITH target_pairs AS (
            SELECT
                w.symbol,
                w.timeframe
            FROM analytics.feature_store_watermark_v1 w
            WHERE (%s::text IS NULL OR w.symbol = %s)
              AND (%s::text IS NULL OR w.timeframe = %s)
        ),
        recent_market_bars AS MATERIALIZED (
            SELECT
                target.symbol,
                target.timeframe,
                source_bar.ts,
                source_bar.open,
                source_bar.high,
                source_bar.low,
                source_bar.close,
                source_bar.volume
            FROM target_pairs target
            CROSS JOIN LATERAL (
                SELECT
                    mb.ts,
                    mb.open,
                    mb.high,
                    mb.low,
                    mb.close,
                    mb.volume
                FROM public.market_bars mb
                WHERE mb.symbol = target.symbol
                  AND mb.timeframe = target.timeframe
                  AND mb.ts IS NOT NULL
                  AND mb.close IS NOT NULL
                ORDER BY mb.ts DESC
                LIMIT %s
            ) source_bar
        ),
        comparison AS (
            SELECT
                source.symbol,
                source.timeframe,
                source.ts,
                snapshot.bar_ts,
                (
                    snapshot.bar_ts IS NULL
                    OR snapshot.open IS DISTINCT FROM source.open
                    OR snapshot.high IS DISTINCT FROM source.high
                    OR snapshot.low IS DISTINCT FROM source.low
                    OR snapshot.close IS DISTINCT FROM source.close
                    OR (
                            snapshot.volume IS NULL
                            AND source.volume IS NOT NULL
                        )
                        OR (
                            snapshot.volume IS NOT NULL
                            AND source.volume IS NULL
                        )
                        OR (
                            snapshot.volume IS NOT NULL
                            AND source.volume IS NOT NULL
                            AND abs(
                                snapshot.volume - source.volume
                            ) > %s::numeric
                        )
                ) AS changed,
                snapshot.bar_ts IS NULL
                    AS missing_market_snapshot
            FROM recent_market_bars source
            LEFT JOIN marketcore.market_snapshot_v1 snapshot
              ON snapshot.symbol = source.symbol
             AND snapshot.timeframe = source.timeframe
             AND snapshot.bar_ts = source.ts
        ),
        missing_source AS (
            SELECT
                target.symbol,
                target.timeframe,
                snapshot.bar_ts AS ts
            FROM target_pairs target
            CROSS JOIN LATERAL (
                SELECT
                    ms.bar_ts
                FROM marketcore.market_snapshot_v1 ms
                WHERE ms.symbol = target.symbol
                  AND ms.timeframe = target.timeframe
                ORDER BY ms.bar_ts DESC
                LIMIT %s
            ) snapshot
            LEFT JOIN public.market_bars source
              ON source.symbol = target.symbol
             AND source.timeframe = target.timeframe
             AND source.ts = snapshot.bar_ts
            WHERE source.ts IS NULL
        ),
        pair_summary AS (
            SELECT
                target.symbol,
                target.timeframe,
                count(comparison.ts)::integer
                    AS checked_rows,
                count(*) FILTER (
                    WHERE comparison.changed
                )::integer AS changed_rows,
                count(*) FILTER (
                    WHERE comparison.missing_market_snapshot
                )::integer AS missing_market_snapshot_rows,
                (
                    SELECT count(*)::integer
                    FROM missing_source missing
                    WHERE missing.symbol = target.symbol
                      AND missing.timeframe = target.timeframe
                ) AS missing_market_bar_rows,
                min(comparison.ts) FILTER (
                    WHERE comparison.changed
                ) AS first_changed_ts,
                max(comparison.ts) FILTER (
                    WHERE comparison.changed
                ) AS last_changed_ts
            FROM target_pairs target
            LEFT JOIN comparison
              ON comparison.symbol = target.symbol
             AND comparison.timeframe = target.timeframe
            GROUP BY
                target.symbol,
                target.timeframe
        )
        SELECT
            symbol,
            timeframe,
            checked_rows,
            changed_rows,
            missing_market_snapshot_rows,
            missing_market_bar_rows,
            first_changed_ts,
            last_changed_ts,
            (
                changed_rows > 0
                OR missing_market_bar_rows > 0
            ) AS correction_detected
        FROM pair_summary
        ORDER BY symbol, timeframe
        """,
        (
            symbol,
            symbol,
            timeframe,
            timeframe,
            window_bars,
            VOLUME_TOLERANCE,
            window_bars,
        ),
    )

    rows = [
        dict(row)
        for row in cur.fetchall()
    ]

    changed_pairs = [
        row
        for row in rows
        if row["correction_detected"]
    ]

    dirty_rows_updated = 0

    if not dry_run:
        audit_rows = [
            (
                str(uuid.uuid4()),
                audit_run_id,
                row["symbol"],
                row["timeframe"],
                int(row["checked_rows"] or 0),
                int(row["changed_rows"] or 0),
                int(
                    row["missing_market_snapshot_rows"]
                    or 0
                ),
                int(
                    row["missing_market_bar_rows"]
                    or 0
                ),
                row["first_changed_ts"],
                row["last_changed_ts"],
                bool(row["correction_detected"]),
                False,
                SOURCE_VERSION,
            )
            for row in rows
        ]

        if audit_rows:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO
                    analytics.feature_store_historical_correction_audit_v1 (
                        audit_id,
                        audit_run_id,
                        symbol,
                        timeframe,
                        checked_rows,
                        changed_rows,
                        missing_market_snapshot_rows,
                        missing_market_bar_rows,
                        first_changed_ts,
                        last_changed_ts,
                        correction_detected,
                        dry_run,
                        source_version
                    )
                VALUES %s
                """,
                audit_rows,
                page_size=500,
            )

        if changed_pairs:
            changed_values = [
                (
                    row["symbol"],
                    row["timeframe"],
                )
                for row in changed_pairs
            ]

            # execute_values не поддерживает дополнительный
            # positional-параметр перед VALUES. Выполняем
            # безопасное параметризованное обновление отдельно.
            cur.execute(
                """
                UPDATE analytics.feature_store_watermark_v1 w
                SET
                    market_dirty = true,
                    market_dirty_at = clock_timestamp(),
                    source_version = %s,
                    updated_at = clock_timestamp()
                WHERE EXISTS (
                    SELECT 1
                    FROM
                        analytics.feature_store_historical_correction_audit_v1 audit
                    WHERE audit.audit_run_id = %s::uuid
                      AND audit.correction_detected
                      AND audit.symbol = w.symbol
                      AND audit.timeframe = w.timeframe
                )
                  AND NOT w.market_dirty
                """,
                (
                    SOURCE_VERSION,
                    audit_run_id,
                ),
            )
            dirty_rows_updated = cur.rowcount

    return AuditSummary(
        checked_pairs=len(rows),
        checked_rows=sum(
            int(row["checked_rows"] or 0)
            for row in rows
        ),
        changed_pairs=len(changed_pairs),
        changed_rows=sum(
            int(row["changed_rows"] or 0)
            for row in rows
        ),
        missing_market_snapshot_rows=sum(
            int(
                row["missing_market_snapshot_rows"]
                or 0
            )
            for row in rows
        ),
        missing_market_bar_rows=sum(
            int(row["missing_market_bar_rows"] or 0)
            for row in rows
        ),
        dirty_rows_updated=dirty_rows_updated,
    )


def main() -> int:
    args = parse_args()
    window_bars = validate_window_bars(
        args.window_bars
    )
    audit_run_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            ensure_contract(cur)

            summary = audit_pairs(
                cur,
                audit_run_id=audit_run_id,
                window_bars=window_bars,
                dry_run=args.dry_run,
                symbol=args.symbol,
                timeframe=args.timeframe,
            )

            if args.dry_run:
                conn.rollback()
            else:
                conn.commit()

    print(
        "=== FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1 ==="
    )
    print(f"audit_run_id={audit_run_id}")
    print(f"window_bars={window_bars}")
    print(f"checked_pairs={summary.checked_pairs}")
    print(f"checked_rows={summary.checked_rows}")
    print(f"changed_pairs={summary.changed_pairs}")
    print(f"changed_rows={summary.changed_rows}")
    print(
        "missing_market_snapshot_rows="
        f"{summary.missing_market_snapshot_rows}"
    )
    print(
        "missing_market_bar_rows="
        f"{summary.missing_market_bar_rows}"
    )
    print(
        "dirty_rows_updated="
        f"{summary.dirty_rows_updated}"
    )
    print(f"dry_run={int(args.dry_run)}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
