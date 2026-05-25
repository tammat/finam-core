from __future__ import annotations

import os
import psycopg


KEEP_REGIME = "LOW_IMPULSE"
KEEP_TREND = "down"
KEEP_VOLATILITY = "high"


def calc_metrics(rows: list[float]) -> dict[str, float]:
    trades = len(rows)
    wins = sum(1 for x in rows if x > 0)
    losses = sum(1 for x in rows if x <= 0)
    gross_profit = sum(x for x in rows if x > 0)
    gross_loss = abs(sum(x for x in rows if x < 0))
    expectancy = sum(rows) / trades if trades else 0.0
    pf = gross_profit / gross_loss if gross_loss else 0.0
    net_pnl = sum(rows)
    winrate = wins / trades if trades else 0.0

    return {
        "trades": float(trades),
        "wins": float(wins),
        "losses": float(losses),
        "net_pnl": net_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "expectancy": expectancy,
        "profit_factor": pf,
        "winrate": winrate,
    }


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    SELECT
        tcs.regime,
        tcs.trend,
        tcs.volatility,
        tcs.lifecycle_state,
        a.pnl
    FROM trade_context_snapshots tcs
    JOIN trade_attribution_v2 a
      ON a.closed_trade_id = tcs.closed_trade_id
    WHERE tcs.symbol = 'BRM6@RTSX'
      AND tcs.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND a.strategy = 'BR_CONSERVATIVE_BREAKOUT'
      AND tcs.context_quality = 'FULL'
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    baseline = [float(row[4] or 0.0) for row in rows]
    filtered = [
        float(row[4] or 0.0)
        for row in rows
        if row[0] == KEEP_REGIME
        and row[1] == KEEP_TREND
        and row[2] == KEEP_VOLATILITY
    ]

    baseline_m = calc_metrics(baseline)
    filtered_m = calc_metrics(filtered)

    baseline_trades = baseline_m["trades"]
    filtered_trades = filtered_m["trades"]

    trade_coverage = filtered_trades / baseline_trades if baseline_trades else 0.0
    pnl_retention = (
        filtered_m["net_pnl"] / baseline_m["net_pnl"]
        if baseline_m["net_pnl"]
        else 0.0
    )
    pnl_delta = filtered_m["net_pnl"] - baseline_m["net_pnl"]
    pf_delta = filtered_m["profit_factor"] - baseline_m["profit_factor"]
    expectancy_delta = filtered_m["expectancy"] - baseline_m["expectancy"]

    print("BR_COVERAGE_IMPACT_REPORT_V1")
    print("scope | trades | wins | losses | winrate | net_pnl | gross_profit | gross_loss | expectancy | pf")

    for name, metrics in (("BASELINE_FULL_CONTEXT", baseline_m), ("FILTER_LOW_IMPULSE_DOWN_HIGH", filtered_m)):
        print(
            f"{name} | "
            f"{int(metrics['trades'])} | "
            f"{int(metrics['wins'])} | "
            f"{int(metrics['losses'])} | "
            f"{metrics['winrate']:.6f} | "
            f"{metrics['net_pnl']:.6f} | "
            f"{metrics['gross_profit']:.6f} | "
            f"{metrics['gross_loss']:.6f} | "
            f"{metrics['expectancy']:.6f} | "
            f"{metrics['profit_factor']:.6f}"
        )

    print("IMPACT")
    print(f"trade_coverage={trade_coverage:.6f}")
    print(f"pnl_retention={pnl_retention:.6f}")
    print(f"pnl_delta={pnl_delta:.6f}")
    print(f"pf_delta={pf_delta:.6f}")
    print(f"expectancy_delta={expectancy_delta:.6f}")
    print(
        "BR_COVERAGE_IMPACT_REPORT_V1_OK "
        f"baseline_trades={int(baseline_trades)} "
        f"filtered_trades={int(filtered_trades)} "
        f"trade_coverage={trade_coverage:.6f}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
