#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from collections import defaultdict, deque
from datetime import timezone, timedelta

import psycopg
from psycopg.rows import dict_row


SYMBOL = os.getenv("SYMBOL", "NGN6@RTSX")
INCLUDE_BATCH = os.getenv("INCLUDE_BATCH", "0") == "1"
MSK = timezone(timedelta(hours=3))


def pf(pnls: list[float]):
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    if gl == 0:
        return None if gp == 0 else "inf"
    return round(gp / gl, 6)


def stats(pnls: list[float]) -> dict:
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    n = len(pnls)
    return {
        "trades": n,
        "pnl": round(sum(pnls), 6),
        "wins": len(wins),
        "losses": len(losses),
        "winrate": round(len(wins) / n, 6) if n else None,
        "expectancy": round(sum(pnls) / n, 6) if n else None,
        "profit_factor": pf(pnls),
    }


def reconstruct_closed_trades(fills: list[dict]) -> list[dict]:
    open_buys = deque()
    closed = []

    for f in fills:
        side = str(f["side"]).upper()
        qty = float(f["qty"] or 0.0)
        price = float(f["price"] or 0.0)
        ts = f["ts"]

        if qty <= 0 or price <= 0:
            continue

        if side == "BUY":
            open_buys.append({"qty": qty, "price": price, "ts": ts})
            continue

        if side != "SELL":
            continue

        remaining = qty
        while remaining > 0 and open_buys:
            b = open_buys[0]
            matched = min(remaining, b["qty"])
            pnl = (price - b["price"]) * matched

            exit_msk = ts.astimezone(MSK)
            entry_msk = b["ts"].astimezone(MSK)

            closed.append({
                "entry_ts": b["ts"],
                "exit_ts": ts,
                "entry_msk": entry_msk,
                "exit_msk": exit_msk,
                "qty": matched,
                "entry": b["price"],
                "exit": price,
                "pnl": pnl,
                "hour_msk": exit_msk.hour,
                "weekday": exit_msk.strftime("%A"),
                "date_msk": exit_msk.date().isoformat(),
            })

            b["qty"] -= matched
            remaining -= matched

            if b["qty"] <= 1e-12:
                open_buys.popleft()

    return closed


def share(part: float, total: float):
    if abs(total) <= 1e-12:
        return None
    return round(part / total, 6)


def print_bucket(title: str, grouped: dict):
    print(title)
    for key in sorted(grouped):
        s = stats(grouped[key])
        print(
            f"{key} trades={s['trades']} pnl={s['pnl']} "
            f"winrate={s['winrate']} expectancy={s['expectancy']} "
            f"profit_factor={s['profit_factor']}"
        )
    print()


def main() -> int:
    db = os.getenv("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(db, row_factory=dict_row) as conn:
        fills = conn.execute(
            """
            SELECT fill_id, ts, symbol, side, qty, price, COALESCE(commission, 0) AS commission
            FROM fills
            WHERE symbol = %s
              AND qty > 0
              AND price > 0
            ORDER BY ts, fill_id
            """,
            (SYMBOL,),
        ).fetchall()

    closed_all = reconstruct_closed_trades(list(fills))
    closed_qty1 = [t for t in closed_all if abs(float(t["qty"]) - 1.0) < 1e-9]
    closed_batch = [t for t in closed_all if float(t["qty"]) > 1.0]

    primary = closed_all if INCLUDE_BATCH else closed_qty1

    pnls = [float(t["pnl"]) for t in primary]
    all_pnls = [float(t["pnl"]) for t in closed_all]
    batch_pnls = [float(t["pnl"]) for t in closed_batch]

    by_weekday = defaultdict(list)
    by_hour = defaultdict(list)
    by_date = defaultdict(list)

    for t in primary:
        by_weekday[t["weekday"]].append(float(t["pnl"]))
        by_hour[t["hour_msk"]].append(float(t["pnl"]))
        by_date[t["date_msk"]].append(float(t["pnl"]))

    total_pnl = sum(pnls)
    positive = sorted([x for x in pnls if x > 0], reverse=True)
    top1 = positive[:1]
    top3 = positive[:3]
    top20_count = max(1, int(len(pnls) * 0.2)) if pnls else 0
    top20 = positive[:top20_count]

    pos_hours = sum(1 for arr in by_hour.values() if sum(arr) > 0)
    neg_hours = sum(1 for arr in by_hour.values() if sum(arr) < 0)
    pos_days = sum(1 for arr in by_date.values() if sum(arr) > 0)
    neg_days = sum(1 for arr in by_date.values() if sum(arr) < 0)

    primary_stats = stats(pnls)

    sample_score = min(25, len(primary) * 25 // 30)
    pf_value = primary_stats["profit_factor"]
    pf_score = 0
    if pf_value == "inf":
        pf_score = 25
    elif isinstance(pf_value, (int, float)):
        if pf_value >= 1.5:
            pf_score = 25
        elif pf_value >= 1.3:
            pf_score = 18
        elif pf_value >= 1.1:
            pf_score = 10

    exp = primary_stats["expectancy"] or 0
    expectancy_score = 25 if exp > 0.01 else 15 if exp > 0 else 0

    top1_share = share(sum(top1), total_pnl)
    concentration_penalty = 0
    if top1_share is not None and top1_share > 0.7:
        concentration_penalty = 25
    elif top1_share is not None and top1_share > 0.5:
        concentration_penalty = 15
    elif top1_share is not None and top1_share > 0.3:
        concentration_penalty = 8

    stability_score = max(0, sample_score + pf_score + expectancy_score - concentration_penalty)

    if len(primary) < 30:
        status = "WEAK"
        reason = "insufficient_sample"
    elif stability_score < 20:
        status = "VERY_WEAK"
        reason = "low_stability_score"
    elif stability_score < 40:
        status = "WEAK"
        reason = "weak_temporal_stability"
    elif stability_score < 60:
        status = "MODERATE"
        reason = "moderate_temporal_stability"
    else:
        status = "STABLE"
        reason = "edge_persistent_enough"

    print("=== NG TEMPORAL STABILITY V1 ===")
    print(f"symbol={SYMBOL}")
    print(f"primary_scope={'ALL' if INCLUDE_BATCH else 'QTY_EQ_1'}")
    print()

    print("SUMMARY")
    print(f"fills={len(fills)}")
    print(f"closed_trades_all={len(closed_all)}")
    print(f"closed_trades_qty1={len(closed_qty1)}")
    print(f"closed_trades_batch_qty_gt_1={len(closed_batch)}")
    print(f"primary_closed_trades={len(primary)}")
    print(f"primary_pnl={primary_stats['pnl']}")
    print(f"primary_winrate={primary_stats['winrate']}")
    print(f"primary_expectancy={primary_stats['expectancy']}")
    print(f"primary_profit_factor={primary_stats['profit_factor']}")
    print()

    print("BATCH_IMPACT")
    print(f"all_pnl={round(sum(all_pnls), 6)}")
    print(f"qty1_pnl={round(sum(pnls), 6)}")
    print(f"batch_pnl={round(sum(batch_pnls), 6)}")
    print(f"batch_trades={len(closed_batch)}")
    print()

    print_bucket("BY_WEEKDAY", by_weekday)
    print_bucket("BY_HOUR_MSK", by_hour)
    print_bucket("BY_DATE_MSK", by_date)

    print("PROFIT_CONCENTRATION")
    print(f"top_1_trade_pnl={round(sum(top1), 6) if top1 else 0}")
    print(f"top_1_trade_share={top1_share}")
    print(f"top_3_trades_pnl={round(sum(top3), 6) if top3 else 0}")
    print(f"top_3_trades_share={share(sum(top3), total_pnl)}")
    print(f"top_20pct_trades_pnl={round(sum(top20), 6) if top20 else 0}")
    print(f"top_20pct_trades_share={share(sum(top20), total_pnl)}")
    print()

    print("EDGE_PERSISTENCE")
    print(f"positive_hours={pos_hours}")
    print(f"negative_hours={neg_hours}")
    print(f"positive_dates={pos_days}")
    print(f"negative_dates={neg_days}")
    print()

    print("STABILITY_SCORE")
    print(f"sample_score={sample_score}")
    print(f"pf_score={pf_score}")
    print(f"expectancy_score={expectancy_score}")
    print(f"concentration_penalty={concentration_penalty}")
    print(f"stability_score={stability_score}")
    print()

    print("FINAL_VERDICT")
    print(f"status={status}")
    print(f"reason={reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
