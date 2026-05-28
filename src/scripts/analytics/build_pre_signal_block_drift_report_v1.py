from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
WITH pre AS (
    SELECT
        symbol,
        strategy,
        timeframe,
        block_type,
        block_reason,
        count(*) AS blocked_total,
        avg(atr_pct) AS avg_block_atr_pct,
        avg(threshold) AS avg_threshold,
        avg(compression_ratio) AS avg_compression_ratio,
        min(ts) AS first_block_ts,
        max(ts) AS last_block_ts
    FROM runtime_guard_pre_signal_block_audit_v1
    GROUP BY
        symbol,
        strategy,
        timeframe,
        block_type,
        block_reason
),
sig AS (
    SELECT
        symbol,
        strategy,
        timeframe,
        count(*) AS signals_total,
        count(*) FILTER (
            WHERE outcome_class IN ('WIN', 'LOSS', 'FLAT')
        ) AS closed_total,
        count(*) FILTER (
            WHERE outcome_class = 'WIN'
        ) AS wins,
        count(*) FILTER (
            WHERE outcome_class = 'LOSS'
        ) AS losses,
        sum(COALESCE(pnl, 0.0)) AS net_pnl,
        avg(pnl) FILTER (
            WHERE pnl IS NOT NULL
        ) AS expectancy
    FROM signal_quality_audit_v1
    GROUP BY
        symbol,
        strategy,
        timeframe
)
SELECT
    pre.symbol,
    pre.strategy,
    pre.timeframe,
    pre.block_type,
    pre.block_reason,

    pre.blocked_total,
    sig.signals_total,
    sig.closed_total,
    sig.wins,
    sig.losses,

    round(pre.avg_block_atr_pct::numeric, 6) AS avg_block_atr_pct,
    round(pre.avg_threshold::numeric, 6) AS avg_threshold,
    round(pre.avg_compression_ratio::numeric, 6) AS avg_compression_ratio,

    round(
        (
            pre.blocked_total::numeric
            /
            NULLIF(pre.blocked_total + COALESCE(sig.signals_total, 0), 0)
        ),
        4
    ) AS block_ratio,

    round(sig.expectancy::numeric, 6) AS realized_expectancy,
    round(sig.net_pnl::numeric, 6) AS realized_net_pnl,

    CASE
        WHEN COALESCE(sig.closed_total, 0) < 30
            THEN 'INSUFFICIENT_DATA'

        WHEN (
            pre.blocked_total::numeric
            /
            NULLIF(pre.blocked_total + COALESCE(sig.signals_total, 0), 0)
        ) > 0.85
        AND COALESCE(sig.expectancy, 0.0) > 0
            THEN 'OVERBLOCKING_RISK'

        WHEN (
            pre.blocked_total::numeric
            /
            NULLIF(pre.blocked_total + COALESCE(sig.signals_total, 0), 0)
        ) < 0.10
        AND COALESCE(sig.expectancy, 0.0) < 0
            THEN 'UNDERFILTERING_RISK'

        WHEN COALESCE(sig.expectancy, 0.0) > 0
            THEN 'HEALTHY'

        ELSE 'NEUTRAL'
    END AS drift_status,

    pre.first_block_ts,
    pre.last_block_ts

FROM pre
LEFT JOIN sig
  ON sig.symbol = pre.symbol
 AND sig.strategy = pre.strategy
 AND sig.timeframe = pre.timeframe

ORDER BY
    pre.blocked_total DESC,
    pre.last_block_ts DESC
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    print("PRE_SIGNAL_BLOCK_DRIFT_REPORT_V1", flush=True)

    for r in rows:
        print(
            "PRE_SIGNAL_BLOCK_DRIFT_ROW",
            f"symbol={r['symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"block_type={r['block_type']}",
            f"blocked={r['blocked_total']}",
            f"signals={r['signals_total']}",
            f"closed={r['closed_total']}",
            f"block_ratio={r['block_ratio']}",
            f"expectancy={r['realized_expectancy']}",
            f"net_pnl={r['realized_net_pnl']}",
            f"drift_status={r['drift_status']}",
            flush=True,
        )

    print(
        f"PRE_SIGNAL_BLOCK_DRIFT_REPORT_V1_OK rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
