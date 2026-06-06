#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


SYMBOLS = ("NGN6@RTSX",)


def fmt_num(v) -> str:
    if v is None:
        return "None"
    try:
        return f"{float(v):.6f}"
    except Exception:
        return str(v)


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== NG SHORT QUALITY AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("goal=measure_NG_OPEN_SHORT_to_CLOSE_SHORT_quality")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            sql = """
            with ordered as (
                select
                    id,
                    ts,
                    symbol,
                    upper(side) as side,
                    qty::numeric as qty,
                    price::numeric as price,
                    coalesce(nullif(strategy,''), payload->>'strategy', 'UNKNOWN') as strategy,
                    coalesce(timeframe, payload->>'timeframe', 'UNKNOWN') as timeframe,
                    coalesce(origin, 'UNKNOWN') as origin,
                    coalesce(payload->>'reason', 'UNKNOWN') as reason,
                    coalesce(commission, 0)::numeric as commission
                from trades
                where symbol = any(%s)
                  and coalesce(trade_source, '') = 'paper'
                  and coalesce(is_invalid, false) = false
                  and upper(side) in ('BUY','SELL')
                order by symbol, ts, id
            ),
            pos as (
                select
                    *,
                    coalesce(
                        sum(case when side='BUY' then qty else -qty end)
                        over (
                            partition by symbol
                            order by ts, id
                            rows between unbounded preceding and 1 preceding
                        ),
                        0
                    ) as position_before
                from ordered
            ),
            actions as (
                select
                    *,
                    position_before + case when side='BUY' then qty else -qty end as position_after,
                    case
                        when side='SELL' and position_before = 0 then 'OPEN_SHORT'
                        when side='BUY' and position_before < 0 and position_before + qty = 0 then 'CLOSE_SHORT'
                        when side='BUY' and position_before < 0 then 'REDUCE_SHORT'
                        when side='SELL' and position_before < 0 then 'ADD_SHORT'
                        when side='BUY' and position_before = 0 then 'OPEN_LONG'
                        when side='SELL' and position_before > 0 and position_before - qty = 0 then 'CLOSE_LONG'
                        when side='SELL' and position_before > 0 then 'REDUCE_LONG'
                        when side='BUY' and position_before > 0 then 'ADD_LONG'
                        else 'UNKNOWN'
                    end as action
                from pos
            ),
            short_entries as (
                select
                    *,
                    row_number() over (partition by symbol order by ts, id) as rn
                from actions
                where action='OPEN_SHORT'
            ),
            short_exits as (
                select
                    *,
                    row_number() over (partition by symbol order by ts, id) as rn
                from actions
                where action='CLOSE_SHORT'
            ),
            paired as (
                select
                    e.symbol,
                    e.strategy,
                    e.timeframe,
                    e.reason as entry_reason,
                    e.origin as entry_origin,
                    e.id as entry_trade_id,
                    x.id as exit_trade_id,
                    e.ts as entry_ts,
                    x.ts as exit_ts,
                    e.price as entry_price,
                    x.price as exit_price,
                    least(e.qty, x.qty) as qty,
                    e.commission + x.commission as commission,
                    (e.price - x.price) * least(e.qty, x.qty) as gross_pnl,
                    ((e.price - x.price) * least(e.qty, x.qty)) - (e.commission + x.commission) as net_pnl,
                    extract(epoch from (x.ts - e.ts)) as holding_seconds,
                    extract(hour from e.ts at time zone 'Europe/Moscow') as entry_hour_msk
                from short_entries e
                join short_exits x
                  on x.symbol = e.symbol
                 and x.rn = e.rn
                 and x.ts > e.ts
            )
            select * from paired
            order by entry_ts;
            """

            cur.execute(sql, (list(SYMBOLS),))
            rows = cur.fetchall()

            print("SUMMARY")
            trades = len(rows)
            wins = sum(1 for r in rows if float(r["net_pnl"] or 0) > 0)
            losses = sum(1 for r in rows if float(r["net_pnl"] or 0) < 0)
            flats = trades - wins - losses
            gross = sum(float(r["gross_pnl"] or 0) for r in rows)
            net = sum(float(r["net_pnl"] or 0) for r in rows)
            win_sum = sum(float(r["net_pnl"] or 0) for r in rows if float(r["net_pnl"] or 0) > 0)
            loss_sum = sum(float(r["net_pnl"] or 0) for r in rows if float(r["net_pnl"] or 0) < 0)
            pf = None if loss_sum == 0 else win_sum / abs(loss_sum)
            expectancy = None if trades == 0 else net / trades
            winrate = None if trades == 0 else wins / trades

            print(f"SHORT_TRADES={trades}")
            print(f"WINS={wins}")
            print(f"LOSSES={losses}")
            print(f"FLATS={flats}")
            print(f"WINRATE={fmt_num(winrate)}")
            print(f"GROSS_PNL={fmt_num(gross)}")
            print(f"NET_PNL={fmt_num(net)}")
            print(f"EXPECTANCY={fmt_num(expectancy)}")
            print(f"PROFIT_FACTOR={fmt_num(pf)}")
            print()

            print("BY_STRATEGY")
            by_strategy: dict[str, list] = {}
            for r in rows:
                by_strategy.setdefault(str(r["strategy"] or "UNKNOWN"), []).append(r)

            for strategy, items in sorted(by_strategy.items()):
                n = len(items)
                w = sum(1 for r in items if float(r["net_pnl"] or 0) > 0)
                l = sum(1 for r in items if float(r["net_pnl"] or 0) < 0)
                net_s = sum(float(r["net_pnl"] or 0) for r in items)
                win_s = sum(float(r["net_pnl"] or 0) for r in items if float(r["net_pnl"] or 0) > 0)
                loss_s = sum(float(r["net_pnl"] or 0) for r in items if float(r["net_pnl"] or 0) < 0)
                pf_s = None if loss_s == 0 else win_s / abs(loss_s)
                print(
                    f"STRATEGY_ROW strategy={strategy} trades={n} "
                    f"wins={w} losses={l} winrate={fmt_num(w / n if n else None)} "
                    f"net_pnl={fmt_num(net_s)} expectancy={fmt_num(net_s / n if n else None)} "
                    f"profit_factor={fmt_num(pf_s)}"
                )
            print()

            print("BY_ENTRY_REASON")
            by_reason: dict[str, list] = {}
            for r in rows:
                by_reason.setdefault(str(r["entry_reason"] or "UNKNOWN"), []).append(r)

            for reason, items in sorted(by_reason.items(), key=lambda kv: len(kv[1]), reverse=True)[:30]:
                n = len(items)
                net_r = sum(float(r["net_pnl"] or 0) for r in items)
                w = sum(1 for r in items if float(r["net_pnl"] or 0) > 0)
                l = sum(1 for r in items if float(r["net_pnl"] or 0) < 0)
                print(
                    f"REASON_ROW reason={reason} trades={n} wins={w} losses={l} "
                    f"net_pnl={fmt_num(net_r)} expectancy={fmt_num(net_r / n if n else None)}"
                )
            print()

            print("BY_ENTRY_HOUR_MSK")
            by_hour: dict[int, list] = {}
            for r in rows:
                by_hour.setdefault(int(r["entry_hour_msk"]), []).append(r)

            for hour, items in sorted(by_hour.items()):
                n = len(items)
                net_h = sum(float(r["net_pnl"] or 0) for r in items)
                w = sum(1 for r in items if float(r["net_pnl"] or 0) > 0)
                l = sum(1 for r in items if float(r["net_pnl"] or 0) < 0)
                print(
                    f"HOUR_ROW hour_msk={hour} trades={n} wins={w} losses={l} "
                    f"winrate={fmt_num(w / n if n else None)} "
                    f"net_pnl={fmt_num(net_h)} expectancy={fmt_num(net_h / n if n else None)}"
                )
            print()

            print("LATEST_SHORT_TRADES")
            for r in rows[-30:]:
                print(
                    f"SHORT_TRADE_ROW symbol={r['symbol']} strategy={r['strategy']} "
                    f"entry_ts={r['entry_ts']} exit_ts={r['exit_ts']} "
                    f"entry={r['entry_price']} exit={r['exit_price']} qty={r['qty']} "
                    f"net_pnl={fmt_num(r['net_pnl'])} hold_sec={fmt_num(r['holding_seconds'])} "
                    f"reason={r['entry_reason']}"
                )
            print()

    if trades < 30:
        verdict = "NG_SHORT_INSUFFICIENT_TRADES"
    elif expectancy is not None and expectancy > 0 and (pf is None or pf > 1.10):
        verdict = "NG_SHORT_EDGE_ACCEPTABLE"
    else:
        verdict = "NG_SHORT_EDGE_WEAK_OR_NEGATIVE"

    print(f"VERDICT={verdict}")
    print("NG_SHORT_QUALITY_AUDIT_V1_OK")


if __name__ == "__main__":
    main()
