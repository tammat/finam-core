from __future__ import annotations

import os
import psycopg


def main() -> None:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    INSERT INTO runtime_strategy_scores (
        strategy,
        root_symbol,
        regime,
        score,
        confidence,
        recommendation,
        source_status,
        trades,
        expectancy,
        profit_factor,
        max_drawdown,
        reason
    )
    SELECT
        strategy,
        CASE
            WHEN symbol LIKE 'NG%@RTSX' THEN 'NG'
            WHEN symbol LIKE 'BR%@RTSX' THEN 'BR'
            WHEN symbol LIKE 'USDRUB%@RTSX' THEN 'USDRUB'
            WHEN symbol LIKE 'CNYRUB%@%' THEN 'CNY'
            WHEN symbol LIKE 'GD%@RTSX' OR symbol LIKE 'GL%@RTSX' THEN 'GOLD'
            WHEN symbol LIKE 'SV%@RTSX' THEN 'SILVER'
            ELSE symbol
        END AS root_symbol,
        COALESCE(NULLIF(timeframe, ''), 'unknown') AS regime,
        CASE
            WHEN enabled THEN 0.60
            WHEN mode = 'RESEARCH_ONLY' THEN 0.30
            ELSE 0.05
        END AS score,
        CASE
            WHEN enabled THEN 0.60
            WHEN mode = 'RESEARCH_ONLY' THEN 0.30
            ELSE 0.10
        END AS confidence,
        mode AS recommendation,
        mode AS source_status,
        0 AS trades,
        0 AS expectancy,
        0 AS profit_factor,
        0 AS max_drawdown,
        reason
    FROM runtime_strategy_selection;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            inserted = cur.rowcount
        conn.commit()

    print(f"RUNTIME_STRATEGY_SCORES_SYNC_OK inserted={inserted}", flush=True)


if __name__ == "__main__":
    main()
