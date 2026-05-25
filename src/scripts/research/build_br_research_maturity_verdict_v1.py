from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg


SYMBOL = "BRM6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
TIMEFRAME = "M5"


@dataclass(frozen=True)
class Verdict:
    final_state: str
    runtime_enabled: bool
    radar_enabled: bool
    reason: str


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        trades,
        profit_factor,
        expectancy,
        status
    FROM strategy_statistics_v2
    WHERE symbol = %(symbol)s
      AND strategy = %(strategy)s
      AND timeframe = %(timeframe)s
      AND trade_source = 'paper'
    ORDER BY calculated_at DESC
    LIMIT 1;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"symbol": SYMBOL, "strategy": STRATEGY, "timeframe": TIMEFRAME})
            row = cur.fetchone()

    if row is None:
        verdict = Verdict(
            final_state="RESEARCH_ONLY",
            runtime_enabled=False,
            radar_enabled=False,
            reason="no_strategy_statistics",
        )
    else:
        trades, pf, expectancy, status = row
        pf = float(pf or 0.0)
        expectancy = float(expectancy or 0.0)

        verdict = Verdict(
            final_state="RESEARCH_WATCH_CONTAMINATED",
            runtime_enabled=False,
            radar_enabled=True,
            reason=(
                "aggregate_edge_weak;"
                "localized_edge_found;"
                "us_open_toxic;"
                "duration_edge_scalp_lt_5m;"
                "repeatability_high_day_concentration;"
                f"trades={trades};pf={pf:.6f};expectancy={expectancy:.6f};status={status}"
            ),
        )

    print("BR_RESEARCH_MATURITY_VERDICT_V1")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"timeframe={TIMEFRAME}")
    print(f"final_state={verdict.final_state}")
    print(f"runtime_enabled={str(verdict.runtime_enabled).lower()}")
    print(f"radar_enabled={str(verdict.radar_enabled).lower()}")
    print(f"reason={verdict.reason}")
    print(
        "BR_RESEARCH_MATURITY_VERDICT_V1_OK "
        f"final_state={verdict.final_state} "
        f"runtime_enabled={str(verdict.runtime_enabled).lower()}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
