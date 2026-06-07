#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

NG_TRUSTED_FROM = "2026-06-03 00:00:00+00"
SOURCE = "closed_trade_engine_v1_1"


def pf(gp: float, gl: float) -> str:
    if gl == 0:
        return "None"
    return f"{gp / abs(gl):.6f}"


def add_metric(stats: dict, key: str, pnl: float) -> None:
    s = stats.setdefault(key, {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "net_pnl": 0.0,
    })
    s["trades"] += 1
    s["net_pnl"] += pnl
    if pnl > 0:
        s["wins"] += 1
        s["gross_profit"] += pnl
    elif pnl < 0:
        s["losses"] += 1
        s["gross_loss"] += pnl


def main() -> None:
    print("=== NG TIME EXIT REPLACEMENT CANDIDATES V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("scope=trusted_time_exit_only")
    print("simulation=proxy_from_closed_trades_not_bar_replay")
    print(f"source={SOURCE}")
    print(f"ng_trusted_from={NG_TRUSTED_FROM}")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    id,
                    symbol,
                    side,
                    entry_price::float AS entry_price,
                    exit_price::float AS exit_price,
                    net_pnl::float AS net_pnl,
                    COALESCE(hold_seconds, holding_seconds, 0)::float AS hold_seconds,
                    COALESCE(mae, 0)::float AS mae,
                    COALESCE(mfe, 0)::float AS mfe,
                    COALESCE((payload->'features'->>'atr')::float, 0) AS atr,
                    COALESCE(exit_ts, closed_at, created_at) AS ts
                FROM closed_trades
                WHERE source = %s
                  AND symbol LIKE 'NG%%'
                  AND COALESCE(NULLIF(payload->>'exit_reason', ''), 'NO_MATCH') = 'time_exit'
                  AND COALESCE(exit_ts, closed_at, created_at) >= %s
                ORDER BY COALESCE(exit_ts, closed_at, created_at), id
            """, (SOURCE, NG_TRUSTED_FROM))
            rows = cur.fetchall()

    stats: dict[str, dict] = {}

    for r in rows:
        pnl = float(r["net_pnl"] or 0.0)
        hold = float(r["hold_seconds"] or 0.0)
        mfe = abs(float(r["mfe"] or 0.0))
        atr = abs(float(r["atr"] or 0.0))

        add_metric(stats, "current_time_exit", pnl)

        # Уже подтвержденная гипотеза: отрицательный time_exit до 60 минут не исполнять.
        if pnl < 0 and hold < 3600:
            add_metric(stats, "hold_bucket_extend_under_60m", 0.0)
        else:
            add_metric(stats, "hold_bucket_extend_under_60m", pnl)

        # Proxy break-even: если сделка была в плюсе по MFE, но закрылась в минус,
        # считаем, что break-even мог бы снизить убыток до 0.
        if pnl < 0 and mfe > 0:
            add_metric(stats, "break_even_proxy", 0.0)
        else:
            add_metric(stats, "break_even_proxy", pnl)

        # Proxy ATR trailing: если MFE >= k*ATR, предполагаем защиту прибыли хотя бы до 0.
        for k, name in [
            (1.0, "atr_trailing_1x_proxy"),
            (1.5, "atr_trailing_1_5x_proxy"),
            (2.0, "atr_trailing_2x_proxy"),
        ]:
            if pnl < 0 and atr > 0 and mfe >= k * atr:
                add_metric(stats, name, 0.0)
            else:
                add_metric(stats, name, pnl)

        # Swing proxy пока самый консервативный: без баров не моделируем.
        add_metric(stats, "swing_low_trail_requires_bar_replay", pnl)

    print("CANDIDATE_RESULTS")
    for name in sorted(stats):
        s = stats[name]
        trades = s["trades"]
        wins = s["wins"]
        losses = s["losses"]
        net = s["net_pnl"]
        expectancy = net / trades if trades else 0.0
        winrate = wins / trades if trades else 0.0
        print(
            f"CANDIDATE_ROW candidate={name} "
            f"trades={trades} wins={wins} losses={losses} "
            f"winrate={winrate:.6f} "
            f"gross_profit={s['gross_profit']:.6f} "
            f"gross_loss={s['gross_loss']:.6f} "
            f"net_pnl={net:.6f} "
            f"expectancy={expectancy:.6f} "
            f"profit_factor={pf(s['gross_profit'], s['gross_loss'])}"
        )
    print()

    print("LIMITATIONS")
    print("LIMIT_ROW reason=proxy_uses_closed_trades_only_not_intrabar_path")
    print("LIMIT_ROW reason=atr_trailing_and_swing_trailing_require_bar_replay_for_final_decision")
    print()

    print("SUMMARY")
    print(f"TRUSTED_TIME_EXIT_ROWS={len(rows)}")
    print("VERDICT=NG_TIME_EXIT_REPLACEMENT_CANDIDATES_RECORDED")
    print("NG_TIME_EXIT_REPLACEMENT_CANDIDATES_V1_OK")


if __name__ == "__main__":
    main()
