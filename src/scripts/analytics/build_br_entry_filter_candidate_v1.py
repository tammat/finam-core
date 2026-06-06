#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict
import psycopg2


def profit_factor(values: list[float]):
    gp = sum(v for v in values if v > 0)
    gl = abs(sum(v for v in values if v < 0))
    return None if gl == 0 else gp / gl


def pct(n: int, d: int) -> float:
    return 0.0 if d == 0 else n / d


def candidate_status(trades: int, mfe_first_rate: float, net_pnl: float, pf):
    if trades >= 10 and mfe_first_rate >= 0.60 and net_pnl > 0 and pf is not None and pf > 1.10:
        return "STRICT_ACCEPT"
    if trades >= 5 and mfe_first_rate >= 0.55 and net_pnl > 0:
        return "SOFT_ACCEPT"
    return "REJECT"


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR ENTRY FILTER CANDIDATE V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("scope=clean_non_quarantined_BR")
    print("criteria_soft=trades>=5,mfe_first_1_rate>=0.55,net_pnl>0")
    print("criteria_strict=trades>=10,mfe_first_1_rate>=0.60,pf>1.10,net_pnl>0")
    print()

    trades_sql = """
        select
            ct.id,
            ct.symbol,
            coalesce(nullif(ct.strategy,''),'UNKNOWN') as strategy,
            ct.entry_price,
            coalesce(ct.opened_at, ct.entry_ts, ct.created_at) as entry_ts,
            coalesce(ct.closed_at, ct.exit_ts, ct.created_at) as exit_ts,
            extract(hour from coalesce(ct.opened_at, ct.entry_ts, ct.created_at) at time zone 'Europe/Moscow') as entry_hour_msk,
            ct.net_pnl
        from closed_trades ct
        where ct.net_pnl is not null
          and ct.symbol = 'BRN6@RTSX'
          and not exists (
              select 1
              from research_closed_trades_quarantine q
              where q.trade_id = ct.id
          )
        order by ct.id;
    """

    bars_sql = """
        select ts, high, low, close
        from market_bars
        where symbol = %s
          and timeframe = 'M5'
          and ts >= %s
          and ts <= %s
        order by ts asc;
    """

    rows = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(trades_sql)
            trades = cur.fetchall()

            for trade_id, symbol, strategy, entry_price, entry_ts, exit_ts, hour_msk, net_pnl in trades:
                cur.execute(bars_sql, (symbol, entry_ts, exit_ts))
                bars = cur.fetchall()

                entry = float(entry_price or 0)

                mfe_1_bar = None
                mae_1_bar = None

                for idx, (ts, high, low, close) in enumerate(bars, start=1):
                    high_f = float(high)
                    low_f = float(low)

                    if mfe_1_bar is None and high_f - entry >= 1.0:
                        mfe_1_bar = idx

                    if mae_1_bar is None and low_f - entry <= -1.0:
                        mae_1_bar = idx

                    if mfe_1_bar is not None and mae_1_bar is not None:
                        break

                if mfe_1_bar is None and mae_1_bar is None:
                    first_touch_1 = "NONE"
                elif mfe_1_bar is not None and mae_1_bar is None:
                    first_touch_1 = "MFE_FIRST"
                elif mfe_1_bar is None and mae_1_bar is not None:
                    first_touch_1 = "MAE_FIRST"
                elif mfe_1_bar <= mae_1_bar:
                    first_touch_1 = "MFE_FIRST"
                else:
                    first_touch_1 = "MAE_FIRST"

                rows.append(
                    {
                        "id": int(trade_id),
                        "strategy": strategy,
                        "hour": int(hour_msk or 0),
                        "net_pnl": float(net_pnl or 0),
                        "first_touch_1": first_touch_1,
                    }
                )

    if not rows:
        print("VERDICT=NO_DATA")
        return

    print(f"TRADES={len(rows)}")
    print()

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for r in rows:
        groups[("strategy", r["strategy"])].append(r)
        groups[("hour_msk", str(r["hour"]))].append(r)
        groups[("strategy_hour", f"{r['strategy']}|hour={r['hour']}")].append(r)

    accepted = []

    print("FILTER_CANDIDATES")

    for (dimension, key), subset in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
        trades_count = len(subset)
        values = [float(r["net_pnl"]) for r in subset]
        net_pnl = sum(values)
        pf = profit_factor(values)
        mfe_first = sum(1 for r in subset if r["first_touch_1"] == "MFE_FIRST")
        mae_first = sum(1 for r in subset if r["first_touch_1"] == "MAE_FIRST")
        none = sum(1 for r in subset if r["first_touch_1"] == "NONE")

        mfe_rate = pct(mfe_first, trades_count)
        mae_rate = pct(mae_first, trades_count)

        status = candidate_status(trades_count, mfe_rate, net_pnl, pf)

        if status != "REJECT":
            accepted.append((dimension, key, status, trades_count, net_pnl, pf, mfe_rate))

        print(
            f"FILTER_ROW dimension={dimension} key={key} "
            f"trades={trades_count} net_pnl={net_pnl:.8f} "
            f"profit_factor={'None' if pf is None else f'{pf:.8f}'} "
            f"mfe_first={mfe_first} mfe_first_rate={mfe_rate:.4f} "
            f"mae_first={mae_first} mae_first_rate={mae_rate:.4f} "
            f"none={none} status={status}"
        )

    print()
    print("ACCEPTED_FILTERS")
    for dimension, key, status, trades_count, net_pnl, pf, mfe_rate in accepted:
        print(
            f"ACCEPTED_ROW dimension={dimension} key={key} status={status} "
            f"trades={trades_count} net_pnl={net_pnl:.8f} "
            f"profit_factor={'None' if pf is None else f'{pf:.8f}'} "
            f"mfe_first_rate={mfe_rate:.4f}"
        )

    print()
    print("RECOMMENDATION")

    if accepted:
        print(f"ACCEPTED_CANDIDATES={len(accepted)}")
        print("DISABLE_RECOMMENDED=0")
        print("VERDICT=FILTER_CANDIDATE_FOUND")
    else:
        print("ACCEPTED_CANDIDATES=0")
        print("DISABLE_RECOMMENDED=1")
        print("BR_LONG_DISABLE_CANDIDATE=1")
        print("VERDICT=NO_FILTER_CANDIDATE")


if __name__ == "__main__":
    main()
