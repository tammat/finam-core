#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

import psycopg2
import psycopg2.extras


SYMBOL = "PLZL@MISX"
STRATEGIES = ("MOEX_SIMPLE_MOMENTUM", "MOEX_MEAN_REVERSION_V1")


@dataclass(frozen=True)
class TradeRow:
    strategy: str
    timeframe: str
    pnl: float
    trade_date: date


def metrics(pnls: list[float]) -> dict[str, float]:
    trades = len(pnls)
    wins = sum(1 for x in pnls if x > 0)
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = abs(sum(x for x in pnls if x < 0))

    if gross_loss > 0:
        pf = gross_profit / gross_loss
    else:
        pf = 999.0 if gross_profit > 0 else 0.0

    return {
        "trades": float(trades),
        "pnl": float(sum(pnls)),
        "expectancy": float(sum(pnls) / trades) if trades else 0.0,
        "winrate": float(wins / trades) if trades else 0.0,
        "profit_factor": float(pf),
    }


def load_rows() -> list[TradeRow]:
    sql = """
    select
        a.strategy,
        a.timeframe,
        a.pnl::float as pnl,
        coalesce(c.exit_ts, a.created_at)::date as trade_date
    from trade_attribution_v2 a
    join closed_trade_chains_v2 c
      on c.id = a.closed_trade_id
    where a.symbol=%s
      and a.strategy = any(%s)
      and a.timeframe='D1'
      and a.trade_source='paper'
    order by a.strategy, trade_date, a.closed_trade_id;
    """

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (SYMBOL, list(STRATEGIES)))
            return [
                TradeRow(
                    strategy=str(r["strategy"]),
                    timeframe=str(r["timeframe"]),
                    pnl=float(r["pnl"] or 0.0),
                    trade_date=r["trade_date"],
                )
                for r in cur.fetchall()
            ]


def main() -> int:
    print("=== PLZL WALKFORWARD ROLLING V2 ===", flush=True)
    print("mode=research_only", flush=True)
    print("date_source=closed_trade_chains_v2.exit_ts", flush=True)
    print("execution_enabled=0", flush=True)

    rows = load_rows()
    grouped: dict[tuple[str, str], list[TradeRow]] = {}

    for r in rows:
        grouped.setdefault((r.strategy, r.timeframe), []).append(r)

    total_windows = 0
    failed_windows = 0

    for (strategy, timeframe), items in grouped.items():
        dates = sorted({x.trade_date for x in items})

        print(
            "PLZL_WF_SERIES "
            f"symbol={SYMBOL} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"trades={len(items)} "
            f"first_trade={dates[0] if dates else 'none'} "
            f"last_trade={dates[-1] if dates else 'none'} "
            f"unique_trade_days={len(dates)}",
            flush=True,
        )

        if len(dates) < 3:
            m = metrics([x.pnl for x in items])
            print(
                "PLZL_WF_LOW_TIME_DIVERSITY "
                f"symbol={SYMBOL} "
                f"strategy={strategy} "
                f"timeframe={timeframe} "
                f"reason=мало_уникальных_торговых_дней "
                f"unique_trade_days={len(dates)} "
                f"trades={int(m['trades'])} "
                f"pnl={m['pnl']:.4f} "
                f"expectancy={m['expectancy']:.4f} "
                f"winrate={m['winrate']:.4f} "
                f"profit_factor={m['profit_factor']:.4f}",
                flush=True,
            )
            failed_windows += 1
            continue

        for split_idx in range(2, len(dates)):
            train_dates = set(dates[:split_idx])
            test_date = dates[split_idx]

            train = [x.pnl for x in items if x.trade_date in train_dates]
            test = [x.pnl for x in items if x.trade_date == test_date]

            train_m = metrics(train)
            test_m = metrics(test)

            total_windows += 1

            status = "OOS_CONFIRMED"
            reason = "rolling_day_oos_ok"

            if int(train_m["trades"]) < 30 or int(test_m["trades"]) < 5:
                status = "LOW_SAMPLE"
                reason = "малая_выборка_rolling_window"
            elif test_m["expectancy"] <= 0 or test_m["profit_factor"] < 1.15:
                status = "OOS_FAILED"
                reason = "rolling_oos_edge_не_подтвержден"

            if status != "OOS_CONFIRMED":
                failed_windows += 1

            print(
                "PLZL_WF_WINDOW "
                f"symbol={SYMBOL} "
                f"strategy={strategy} "
                f"timeframe={timeframe} "
                f"train_days={len(train_dates)} "
                f"test_day={test_date} "
                f"train_trades={int(train_m['trades'])} "
                f"test_trades={int(test_m['trades'])} "
                f"train_pf={train_m['profit_factor']:.4f} "
                f"test_pf={test_m['profit_factor']:.4f} "
                f"test_expectancy={test_m['expectancy']:.4f} "
                f"test_winrate={test_m['winrate']:.4f} "
                f"status={status} "
                f"reason={reason}",
                flush=True,
            )

    print(
        "PLZL_WALKFORWARD_ROLLING_V2_SUMMARY "
        f"series={len(grouped)} "
        f"windows={total_windows} "
        f"failed_or_low_sample={failed_windows} "
        "runtime_allow=0 "
        "execution_enabled=0",
        flush=True,
    )

    print("PLZL_WALKFORWARD_ROLLING_V2_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
