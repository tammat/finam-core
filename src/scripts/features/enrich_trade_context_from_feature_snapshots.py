from __future__ import annotations

import argparse
import os

import psycopg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    database_url = os.environ["DATABASE_URL"]

    sql = """
    WITH target AS (
        SELECT
            tcs.id,
            tcs.closed_trade_id,
            tcs.symbol,
            tcs.timeframe,
            tcs.entry_ts
        FROM trade_context_snapshots tcs
        WHERE tcs.symbol = %(symbol)s
          AND tcs.entry_ts IS NOT NULL
        ORDER BY tcs.entry_ts DESC
        LIMIT %(limit)s
    ),
    matched AS (
        SELECT
            t.id AS trade_context_snapshot_id,
            fs.intermarket_commodity_mode,
            fs.trend_state,
            fs.volatility_state,
            fs.range_state,
            fs.session_state,
            fs.intermarket_risk_mode,
            fs.fx_stress_score,
            fs.commodity_score,
            fs.quality AS feature_quality
        FROM target t
        JOIN LATERAL (
            SELECT *
            FROM feature_snapshots fs
            WHERE fs.symbol = t.symbol
              AND fs.timeframe = CASE
                    WHEN t.timeframe IN ('M1', 'M5', 'M15', 'H1', 'D1') THEN t.timeframe
                    ELSE 'M5'
                  END
              AND fs.ts <= t.entry_ts
            ORDER BY fs.ts DESC
            LIMIT 1
        ) fs ON TRUE
    )
    UPDATE trade_context_snapshots tcs
    SET
        regime = matched.intermarket_commodity_mode,
        trend = matched.trend_state,
        volatility = matched.volatility_state,
        missing_fields = regexp_replace(
            regexp_replace(
                regexp_replace(tcs.missing_fields, '(^|,)regime(,|$)', '\\1', 'g'),
                '(^|,)trend(,|$)', '\\1', 'g'
            ),
            '(^|,)volatility(,|$)', '\\1', 'g'
        ),
        context_quality = CASE
            WHEN matched.feature_quality = 'FULL'
             AND tcs.heat_status <> 'unknown'
             AND COALESCE(tcs.exit_policy, '') <> ''
             AND tcs.lifecycle_state <> 'UNKNOWN'
            THEN 'FULL'
            ELSE 'PARTIAL'
        END,
        updated_at = now()
    FROM matched
    WHERE tcs.id = matched.trade_context_snapshot_id;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"symbol": args.symbol, "limit": args.limit})
            updated = cur.rowcount
        conn.commit()

    print(
        "TRADE_CONTEXT_FEATURE_ENRICHMENT_OK "
        f"symbol={args.symbol} updated={updated}",
        flush=True,
    )


if __name__ == "__main__":
    main()
