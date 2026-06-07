#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


NG_TRUSTED_FROM = "2026-06-03 00:00:00+00"
SOURCE = "closed_trade_engine_v1_1"


def pf_expr() -> str:
    return """
        CASE
            WHEN abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) IS NULL
              OR abs(sum(net_pnl) FILTER (WHERE net_pnl < 0)) = 0
            THEN NULL
            ELSE
                (sum(net_pnl) FILTER (WHERE net_pnl > 0))
                / abs(sum(net_pnl) FILTER (WHERE net_pnl < 0))
        END
    """


def print_rows(title: str, rows, prefix: str, fields: list[str]) -> None:
    print(title)
    if not rows:
        print("NONE")
    for r in rows:
        parts = []
        for f in fields:
            v = r.get(f)
            if isinstance(v, float):
                parts.append(f"{f}={v:.6f}")
            else:
                parts.append(f"{f}={v}")
        print(f"{prefix} " + " ".join(parts))
    print()


def main() -> None:
    print("=== NG EXIT REASON QUALITY DECOMPOSITION V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("scope=trusted_window_only")
    print(f"source={SOURCE}")
    print(f"ng_trusted_from={NG_TRUSTED_FROM}")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    base_cte = f"""
        WITH base AS (
            SELECT
                id,
                symbol,
                side,
                strategy,
                timeframe,
                COALESCE(exit_ts, closed_at, created_at) AS ts,
                EXTRACT(HOUR FROM (COALESCE(exit_ts, closed_at, created_at) AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk,
                COALESCE(NULLIF(payload->>'exit_reason', ''), 'NO_MATCH') AS exit_reason,
                COALESCE(NULLIF(entry_regime, ''), NULLIF(regime, ''), 'unknown') AS regime,
                COALESCE(hold_seconds, holding_seconds, 0)::float AS hold_seconds,
                net_pnl::float AS net_pnl
            FROM closed_trades
            WHERE source = %s
              AND symbol LIKE 'NG%%'
              AND COALESCE(exit_ts, closed_at, created_at) >= %s
        ),
        enriched AS (
            SELECT
                *,
                CASE
                    WHEN hold_seconds < 1800 THEN '0-30m'
                    WHEN hold_seconds < 3600 THEN '30-60m'
                    WHEN hold_seconds < 7200 THEN '1-2h'
                    WHEN hold_seconds < 14400 THEN '2-4h'
                    WHEN hold_seconds < 28800 THEN '4-8h'
                    ELSE '8h+'
                END AS hold_bucket
            FROM base
        )
    """

    metrics = f"""
        count(*) AS trades,
        count(*) FILTER (WHERE net_pnl > 0) AS wins,
        count(*) FILTER (WHERE net_pnl < 0) AS losses,
        round((count(*) FILTER (WHERE net_pnl > 0)::numeric / nullif(count(*),0)), 6)::float AS winrate,
        round(coalesce(sum(net_pnl) FILTER (WHERE net_pnl > 0), 0)::numeric, 6)::float AS gross_profit,
        round(coalesce(sum(net_pnl) FILTER (WHERE net_pnl < 0), 0)::numeric, 6)::float AS gross_loss,
        round(sum(net_pnl)::numeric, 6)::float AS net_pnl,
        round(avg(net_pnl)::numeric, 6)::float AS expectancy,
        round(({pf_expr()})::numeric, 6)::float AS profit_factor
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute(
                base_cte + f"""
                SELECT
                    exit_reason,
                    {metrics}
                FROM enriched
                GROUP BY exit_reason
                ORDER BY trades DESC, exit_reason
                """,
                (SOURCE, NG_TRUSTED_FROM),
            )
            reason_rows = cur.fetchall()

            cur.execute(
                base_cte + f"""
                SELECT
                    exit_reason,
                    hour_msk,
                    {metrics}
                FROM enriched
                GROUP BY exit_reason, hour_msk
                ORDER BY exit_reason, hour_msk
                """,
                (SOURCE, NG_TRUSTED_FROM),
            )
            hour_rows = cur.fetchall()

            cur.execute(
                base_cte + f"""
                SELECT
                    exit_reason,
                    regime,
                    {metrics}
                FROM enriched
                GROUP BY exit_reason, regime
                ORDER BY exit_reason, trades DESC, regime
                """,
                (SOURCE, NG_TRUSTED_FROM),
            )
            regime_rows = cur.fetchall()

            cur.execute(
                base_cte + f"""
                SELECT
                    exit_reason,
                    hold_bucket,
                    {metrics}
                FROM enriched
                GROUP BY exit_reason, hold_bucket
                ORDER BY exit_reason,
                    CASE hold_bucket
                        WHEN '0-30m' THEN 1
                        WHEN '30-60m' THEN 2
                        WHEN '1-2h' THEN 3
                        WHEN '2-4h' THEN 4
                        WHEN '4-8h' THEN 5
                        ELSE 6
                    END
                """,
                (SOURCE, NG_TRUSTED_FROM),
            )
            hold_rows = cur.fetchall()

            cur.execute(
                base_cte + f"""
                SELECT
                    exit_reason,
                    side,
                    {metrics}
                FROM enriched
                GROUP BY exit_reason, side
                ORDER BY exit_reason, side
                """,
                (SOURCE, NG_TRUSTED_FROM),
            )
            side_rows = cur.fetchall()

            cur.execute(
                base_cte + """
                SELECT
                    id,
                    symbol,
                    side,
                    exit_reason,
                    hour_msk,
                    regime,
                    hold_bucket,
                    round(net_pnl::numeric, 6)::float AS net_pnl,
                    ts
                FROM enriched
                WHERE net_pnl < 0
                ORDER BY net_pnl ASC
                LIMIT 20
                """,
                (SOURCE, NG_TRUSTED_FROM),
            )
            loss_rows = cur.fetchall()

    common_fields = [
        "trades",
        "wins",
        "losses",
        "winrate",
        "gross_profit",
        "gross_loss",
        "net_pnl",
        "expectancy",
        "profit_factor",
    ]

    print_rows(
        "EXIT_REASON_SUMMARY",
        reason_rows,
        "REASON_ROW",
        ["exit_reason"] + common_fields,
    )

    print_rows(
        "EXIT_REASON_BY_HOUR_MSK",
        hour_rows,
        "REASON_HOUR_ROW",
        ["exit_reason", "hour_msk"] + common_fields,
    )

    print_rows(
        "EXIT_REASON_BY_REGIME",
        regime_rows,
        "REASON_REGIME_ROW",
        ["exit_reason", "regime"] + common_fields,
    )

    print_rows(
        "EXIT_REASON_BY_HOLD_BUCKET",
        hold_rows,
        "REASON_HOLD_ROW",
        ["exit_reason", "hold_bucket"] + common_fields,
    )

    print_rows(
        "EXIT_REASON_BY_SIDE",
        side_rows,
        "REASON_SIDE_ROW",
        ["exit_reason", "side"] + common_fields,
    )

    print("TOP_LOSS_CLUSTERS")
    if not loss_rows:
        print("NONE")
    for r in loss_rows:
        print(
            f"LOSS_ROW id={r['id']} symbol={r['symbol']} side={r['side']} "
            f"exit_reason={r['exit_reason']} hour_msk={r['hour_msk']} "
            f"regime={r['regime']} hold_bucket={r['hold_bucket']} "
            f"net_pnl={float(r['net_pnl']):.6f} ts={r['ts']}"
        )
    print()

    print("SUMMARY")
    total = sum(int(r["trades"] or 0) for r in reason_rows)
    print(f"TRUSTED_NG_ROWS={total}")
    print("VERDICT=NG_EXIT_QUALITY_DECOMPOSED")
    print("NG_EXIT_REASON_QUALITY_DECOMPOSITION_V1_OK")


if __name__ == "__main__":
    main()
