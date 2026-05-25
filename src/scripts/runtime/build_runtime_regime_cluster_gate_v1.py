from __future__ import annotations

import os
import psycopg


SYMBOL = "BRM6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
TIMEFRAME = "M5"

KEEP_REGIME = "LOW_IMPULSE"
KEEP_TREND = "down"
KEEP_VOLATILITY = "high"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    WITH latest_context AS (
        SELECT
            symbol,
            strategy,
            timeframe,
            regime,
            trend,
            volatility,
            context_quality,
            updated_at
        FROM trade_context_snapshots
        WHERE symbol = %(symbol)s
          AND strategy = %(strategy)s
          AND timeframe = %(timeframe)s
        ORDER BY COALESCE(exit_ts, entry_ts, updated_at) DESC
        LIMIT 1
    )
    SELECT
        symbol,
        strategy,
        timeframe,
        regime,
        trend,
        volatility,
        context_quality,
        updated_at
    FROM latest_context;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                {
                    "symbol": SYMBOL,
                    "strategy": STRATEGY,
                    "timeframe": TIMEFRAME,
                },
            )
            row = cur.fetchone()

    print("RUNTIME_REGIME_CLUSTER_GATE_V1")

    if row is None:
        print("decision=BLOCK")
        print("reason=no_context_snapshot")
        print("RUNTIME_REGIME_CLUSTER_GATE_V1_OK decision=BLOCK")
        return 0

    symbol, strategy, timeframe, regime, trend, volatility, context_quality, updated_at = row

    cluster_match = (
        regime == KEEP_REGIME
        and trend == KEEP_TREND
        and volatility == KEEP_VOLATILITY
        and context_quality == "FULL"
    )

    if cluster_match:
        decision = "ALLOW_RESEARCH_GATE"
        enabled = "false"
        reason = "confirmed_research_cluster_but_runtime_disabled_by_maturity_phase"
    else:
        decision = "BLOCK"
        enabled = "false"
        reason = (
            "cluster_mismatch:"
            f"regime={regime};trend={trend};volatility={volatility};quality={context_quality}"
        )

    print(f"symbol={symbol}")
    print(f"strategy={strategy}")
    print(f"timeframe={timeframe}")
    print(f"regime={regime}")
    print(f"trend={trend}")
    print(f"volatility={volatility}")
    print(f"context_quality={context_quality}")
    print(f"updated_at={updated_at}")
    print(f"decision={decision}")
    print(f"enabled={enabled}")
    print(f"reason={reason}")
    print(f"RUNTIME_REGIME_CLUSTER_GATE_V1_OK decision={decision} enabled={enabled}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
