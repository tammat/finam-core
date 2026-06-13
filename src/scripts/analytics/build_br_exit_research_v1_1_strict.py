#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def profit_factor(values):
    gp = sum(v for v in values if v > 0)
    gl = abs(sum(v for v in values if v < 0))
    return None if gl == 0 else gp / gl


def metrics(policy, values):
    trades = len(values)
    net = sum(values)
    wins = sum(1 for v in values if v > 0)
    pf = profit_factor(values)
    return {
        "policy": policy,
        "trades": trades,
        "net_pnl": net,
        "expectancy": net / trades if trades else 0.0,
        "winrate": wins / trades if trades else 0.0,
        "profit_factor": pf,
        "max_loss": min(values) if values else 0.0,
        "max_win": max(values) if values else 0.0,
    }


def print_policy(prefix, rank, row):
    pf = row["profit_factor"]
    print(
        f"{prefix} rank={rank} policy={row['policy']} "
        f"trades={row['trades']} net_pnl={row['net_pnl']:.8f} "
        f"expectancy={row['expectancy']:.8f} winrate={row['winrate']:.4f} "
        f"profit_factor={'None' if pf is None else f'{pf:.8f}'} "
        f"max_loss={row['max_loss']:.8f} max_win={row['max_win']:.8f}"
    )


def simulate_path(entry_price, net_pnl, bars, *, take=None, stop=None, breakeven_trigger=None, trail_gap=None):
    """
    Последовательная симуляция без look-ahead:
    - LONG only.
    - Проверяем бары по времени.
    - Если high достигает take — фиксируем take.
    - Если low достигает stop/trailing/breakeven — фиксируем соответствующий уровень.
    - Если ничего не сработало — возвращаем фактический net_pnl.
    """
    stop_level = entry_price - stop if stop is not None else None
    breakeven_armed = False
    trailing_stop = None

    for _, high, low, close in bars:
        high = float(high)
        low = float(low)
        close = float(close)

        if breakeven_trigger is not None and high - entry_price >= breakeven_trigger:
            breakeven_armed = True

        if trail_gap is not None and high - entry_price > 0:
            candidate = high - trail_gap
            if trailing_stop is None or candidate > trailing_stop:
                trailing_stop = candidate

        active_stop = stop_level

        if breakeven_armed:
            active_stop = max(active_stop, entry_price) if active_stop is not None else entry_price

        if trailing_stop is not None:
            active_stop = max(active_stop, trailing_stop) if active_stop is not None else trailing_stop

        if active_stop is not None and low <= active_stop:
            return active_stop - entry_price

        if take is not None and high - entry_price >= take:
            return take

    return float(net_pnl or 0)


def main():
    dsn = os.environ["DATABASE_URL"]

    print("=== BR EXIT RESEARCH V1.1 STRICT ===")
    print("mode=research_only")
    print("execution=disabled")
    print("lookahead=disabled")
    print("scope=clean_non_quarantined_BR")
    print()

    trades_sql = """
        select
            ct.id,
            ct.symbol,
            ct.strategy,
            ct.net_pnl,
            ct.entry_price,
            coalesce(ct.opened_at, ct.entry_ts, ct.created_at) as entry_ts,
            coalesce(ct.closed_at, ct.exit_ts, ct.created_at) as exit_ts
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

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(trades_sql)
            trades = cur.fetchall()

            rows = []
            for trade_id, symbol, strategy, net_pnl, entry_price, entry_ts, exit_ts in trades:
                cur.execute(bars_sql, (symbol, entry_ts, exit_ts))
                bars = cur.fetchall()
                rows.append(
                    {
                        "id": trade_id,
                        "symbol": symbol,
                        "strategy": strategy,
                        "net_pnl": float(net_pnl or 0),
                        "entry_price": float(entry_price or 0),
                        "entry_ts": entry_ts,
                        "exit_ts": exit_ts,
                        "bars": bars,
                    }
                )

    if not rows:
        print("VERDICT=NO_DATA")
        return

    policies = {
        "historical_time_exit": [],
        "take1_stop2": [],
        "take1_5_stop2": [],
        "take2_stop2": [],
        "take2_stop3": [],
        "take2_stop4": [],
        "breakeven_after_mfe_1": [],
        "breakeven_after_mfe_1_5": [],
        "breakeven_after_mfe_2": [],
        "trail_gap_1_after_positive": [],
        "trail_gap_1_5_after_positive": [],
        "trail_gap_2_after_positive": [],
    }

    for row in rows:
        entry_price = row["entry_price"]
        net_pnl = row["net_pnl"]
        bars = row["bars"]

        policies["historical_time_exit"].append(net_pnl)

        policies["take1_stop2"].append(
            simulate_path(entry_price, net_pnl, bars, take=1.0, stop=2.0)
        )
        policies["take1_5_stop2"].append(
            simulate_path(entry_price, net_pnl, bars, take=1.5, stop=2.0)
        )
        policies["take2_stop2"].append(
            simulate_path(entry_price, net_pnl, bars, take=2.0, stop=2.0)
        )
        policies["take2_stop3"].append(
            simulate_path(entry_price, net_pnl, bars, take=2.0, stop=3.0)
        )
        policies["take2_stop4"].append(
            simulate_path(entry_price, net_pnl, bars, take=2.0, stop=4.0)
        )

        policies["breakeven_after_mfe_1"].append(
            simulate_path(entry_price, net_pnl, bars, breakeven_trigger=1.0)
        )
        policies["breakeven_after_mfe_1_5"].append(
            simulate_path(entry_price, net_pnl, bars, breakeven_trigger=1.5)
        )
        policies["breakeven_after_mfe_2"].append(
            simulate_path(entry_price, net_pnl, bars, breakeven_trigger=2.0)
        )

        policies["trail_gap_1_after_positive"].append(
            simulate_path(entry_price, net_pnl, bars, trail_gap=1.0)
        )
        policies["trail_gap_1_5_after_positive"].append(
            simulate_path(entry_price, net_pnl, bars, trail_gap=1.5)
        )
        policies["trail_gap_2_after_positive"].append(
            simulate_path(entry_price, net_pnl, bars, trail_gap=2.0)
        )

    results = [metrics(policy, values) for policy, values in policies.items()]

    print("POLICIES")
    for idx, row in enumerate(results, start=1):
        print_policy("POLICY_ROW", idx, row)

    ranked = sorted(
        results,
        key=lambda r: (
            -999999 if r["profit_factor"] is None else r["profit_factor"],
            r["net_pnl"],
        ),
        reverse=True,
    )

    print()
    print("RANKING")
    for idx, row in enumerate(ranked, start=1):
        print_policy("RANK_ROW", idx, row)

    winner = ranked[0]
    winner_pf = winner["profit_factor"]
    winner_pf_text = "None" if winner_pf is None else f"{winner_pf:.8f}"

    print()
    print(
        f"WINNER_POLICY={winner['policy']} "
        f"WINNER_NET_PNL={winner['net_pnl']:.8f} "
        f"WINNER_EXPECTANCY={winner['expectancy']:.8f} "
        f"WINNER_PF={winner_pf_text}"
    )

    if (
        winner["trades"] >= 30
        and winner["net_pnl"] > 0
        and winner["expectancy"] > 0
        and winner["profit_factor"] is not None
        and winner["profit_factor"] > 1.10
    ):
        print("VERDICT=STRICT_EXIT_CANDIDATE_FOUND")
    else:
        print("VERDICT=NO_STRICT_POLICY_PASSED")


if __name__ == "__main__":
    main()
