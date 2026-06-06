#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


LEVELS = (1.0, 2.0)


def pct(v: int, n: int) -> float:
    return 0.0 if n == 0 else v / n


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR ENTRY QUALITY STRICT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("lookahead_decision=disabled")
    print("scope=clean_non_quarantined_BR")
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
                net = float(net_pnl or 0)

                result = {
                    "id": trade_id,
                    "symbol": symbol,
                    "strategy": strategy,
                    "entry_hour_msk": int(hour_msk or 0),
                    "net_pnl": net,
                    "bars": len(bars),
                    "mfe": None,
                    "mae": None,
                }

                highs = [float(b[1]) for b in bars]
                lows = [float(b[2]) for b in bars]

                result["mfe"] = max((h - entry for h in highs), default=0.0)
                result["mae"] = min((l - entry for l in lows), default=0.0)

                for level in LEVELS:
                    mfe_hit_ts = None
                    mae_hit_ts = None
                    mfe_hit_bar = None
                    mae_hit_bar = None

                    for idx, (ts, high, low, close) in enumerate(bars, start=1):
                        high_f = float(high)
                        low_f = float(low)

                        if mfe_hit_ts is None and high_f - entry >= level:
                            mfe_hit_ts = ts
                            mfe_hit_bar = idx

                        if mae_hit_ts is None and low_f - entry <= -level:
                            mae_hit_ts = ts
                            mae_hit_bar = idx

                        if mfe_hit_ts is not None and mae_hit_ts is not None:
                            break

                    result[f"mfe_{level:g}_hit"] = mfe_hit_ts is not None
                    result[f"mae_{level:g}_hit"] = mae_hit_ts is not None
                    result[f"mfe_{level:g}_bar"] = mfe_hit_bar
                    result[f"mae_{level:g}_bar"] = mae_hit_bar

                    if mfe_hit_ts is None and mae_hit_ts is None:
                        first = "NONE"
                    elif mfe_hit_ts is not None and mae_hit_ts is None:
                        first = "MFE_FIRST"
                    elif mfe_hit_ts is None and mae_hit_ts is not None:
                        first = "MAE_FIRST"
                    elif mfe_hit_bar <= mae_hit_bar:
                        first = "MFE_FIRST"
                    else:
                        first = "MAE_FIRST"

                    result[f"first_touch_{level:g}"] = first

                rows.append(result)

    if not rows:
        print("VERDICT=NO_DATA")
        return

    print(f"TRADES={len(rows)}")
    print()

    def summary_block(title: str, subset: list[dict]) -> None:
        n = len(subset)
        if n == 0:
            return

        print(title)
        print(f"ROWS={n}")

        for level in LEVELS:
            level_key = f"{level:g}"

            mfe_hits = sum(1 for r in subset if r[f"mfe_{level_key}_hit"])
            mae_hits = sum(1 for r in subset if r[f"mae_{level_key}_hit"])
            mfe_first = sum(1 for r in subset if r[f"first_touch_{level_key}"] == "MFE_FIRST")
            mae_first = sum(1 for r in subset if r[f"first_touch_{level_key}"] == "MAE_FIRST")
            none_first = sum(1 for r in subset if r[f"first_touch_{level_key}"] == "NONE")

            mfe_bars = [r[f"mfe_{level_key}_bar"] for r in subset if r[f"mfe_{level_key}_bar"] is not None]
            mae_bars = [r[f"mae_{level_key}_bar"] for r in subset if r[f"mae_{level_key}_bar"] is not None]

            avg_mfe_bar = sum(mfe_bars) / len(mfe_bars) if mfe_bars else 0.0
            avg_mae_bar = sum(mae_bars) / len(mae_bars) if mae_bars else 0.0

            print(
                f"LEVEL_ROW level={level_key} "
                f"mfe_hit={mfe_hits} mfe_hit_rate={pct(mfe_hits, n):.4f} "
                f"mae_hit={mae_hits} mae_hit_rate={pct(mae_hits, n):.4f} "
                f"mfe_first={mfe_first} mfe_first_rate={pct(mfe_first, n):.4f} "
                f"mae_first={mae_first} mae_first_rate={pct(mae_first, n):.4f} "
                f"none={none_first} none_rate={pct(none_first, n):.4f} "
                f"avg_mfe_bar={avg_mfe_bar:.2f} avg_mae_bar={avg_mae_bar:.2f}"
            )

        avg_mfe = sum(float(r["mfe"] or 0) for r in subset) / n
        avg_mae = sum(float(r["mae"] or 0) for r in subset) / n
        net_pnl = sum(float(r["net_pnl"] or 0) for r in subset)

        print(f"AGG_ROW avg_mfe={avg_mfe:.8f} avg_mae={avg_mae:.8f} net_pnl={net_pnl:.8f}")
        print()

    summary_block("OVERALL", rows)

    print("BY_STRATEGY")
    for strategy in sorted({r["strategy"] for r in rows}):
        subset = [r for r in rows if r["strategy"] == strategy]
        print(f"STRATEGY={strategy}")
        summary_block("STRATEGY_BLOCK", subset)

    print("BY_ENTRY_HOUR_MSK")
    for hour in sorted({r["entry_hour_msk"] for r in rows}):
        subset = [r for r in rows if r["entry_hour_msk"] == hour]
        print(f"HOUR_MSK={hour}")
        summary_block("HOUR_BLOCK", subset)

    print("TOP_BAD_ENTRIES")
    bad = sorted(
        rows,
        key=lambda r: (
            r["first_touch_1"] == "MAE_FIRST",
            abs(float(r["mae"] or 0)),
            -float(r["net_pnl"] or 0),
        ),
        reverse=True,
    )[:20]

    for r in bad:
        print(
            f"BAD_ENTRY_ROW id={r['id']} strategy={r['strategy']} hour_msk={r['entry_hour_msk']} "
            f"net_pnl={r['net_pnl']:.8f} mfe={r['mfe']:.8f} mae={r['mae']:.8f} "
            f"first_touch_1={r['first_touch_1']} first_touch_2={r['first_touch_2']} "
            f"mfe_1_bar={r['mfe_1_bar']} mae_1_bar={r['mae_1_bar']}"
        )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
