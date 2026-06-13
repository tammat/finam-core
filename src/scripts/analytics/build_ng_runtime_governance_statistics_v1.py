#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from collections import defaultdict
from datetime import timezone, timedelta

import psycopg
from psycopg.rows import dict_row


SYMBOL = os.getenv("SYMBOL", "NGN6@RTSX")
MSK = timezone(timedelta(hours=3))


def msk_hour(ts):
    return ts.astimezone(MSK).hour if ts else None


def session_ru(hour: int | None) -> str:
    if hour is None:
        return "неизвестно"
    if 7 <= hour < 10:
        return "утро_мск"
    if 10 <= hour < 15:
        return "московская_середина"
    if 15 <= hour < 19:
        return "вечерняя_сессия"
    return "вне_основной_сессии"


def safe_pf(wins, losses):
    gross_win = sum(x for x in wins if x > 0)
    gross_loss = abs(sum(x for x in losses if x < 0))
    if gross_loss == 0:
        return None if gross_win == 0 else "inf"
    return round(gross_win / gross_loss, 6)


def print_perf_block(title: str, trades: list[dict]) -> None:
    """Русский комментарий: печатает единый performance-блок по выбранному срезу сделок."""
    pnls = [float(x["pnl_points"]) for x in trades]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]

    print(title)
    print(f"closed_trades={len(trades)}")
    print(f"gross_pnl_points={round(sum(pnls), 6)}")
    print(f"wins={len(wins)}")
    print(f"losses={len(losses)}")
    print(f"winrate={round(len(wins) / len(trades), 6) if trades else None}")
    print(f"expectancy_points={round(sum(pnls) / len(trades), 6) if trades else None}")
    print(f"profit_factor={safe_pf(wins, losses)}")
    print(f"avg_win={round(sum(wins) / len(wins), 6) if wins else None}")
    print(f"avg_loss={round(sum(losses) / len(losses), 6) if losses else None}")
    print()


def main() -> int:
    db = os.getenv("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL is required")

    use_materialized = os.getenv("USE_MATERIALIZED_CLOSED_TRADES", "1") == "1"

    if use_materialized:
        with psycopg.connect(db, row_factory=dict_row) as conn:
            closed_rows = conn.execute(
                """
                SELECT
                    trade_id,
                    symbol,
                    strategy,
                    side,
                    qty,
                    entry_ts,
                    exit_ts,
                    entry_price,
                    exit_price,
                    pnl_points,
                    hour_msk,
                    weekday,
                    session,
                    raw
                FROM analytics_closed_trades_v1
                WHERE symbol = %s
                ORDER BY exit_ts, trade_id
                """,
                (SYMBOL,),
            ).fetchall()

            fill_summary = conn.execute(
                """
                SELECT
                    COUNT(*) AS fills,
                    MIN(ts) AS first_fill,
                    MAX(ts) AS last_fill,
                    COALESCE(SUM(CASE WHEN side='BUY' THEN qty ELSE -qty END), 0) AS open_qty
                FROM fills
                WHERE symbol = %s
                """,
                (SYMBOL,),
            ).fetchone()

            link_summary = conn.execute(
                """
                SELECT COUNT(*) AS signal_links
                FROM signal_fills
                WHERE symbol = %s
                """,
                (SYMBOL,),
            ).fetchone()

        closed = [
            {
                "entry_ts": r["entry_ts"],
                "exit_ts": r["exit_ts"],
                "side": r["side"],
                "close_side": "SELL" if r["side"] == "LONG" else "BUY",
                "qty": float(r["qty"] or 0.0),
                "entry_price": float(r["entry_price"] or 0.0),
                "exit_price": float(r["exit_price"] or 0.0),
                "pnl_points": float(r["pnl_points"] or 0.0),
                "hour_msk": r["hour_msk"],
                "session": r["session"],
                "raw": r.get("raw") or {},
            }
            for r in closed_rows
        ]

        fills = []
        signal_links = [None] * int((link_summary or {}).get("signal_links") or 0)
        open_qty = float((fill_summary or {}).get("open_qty") or 0.0)
        first_fill = (fill_summary or {}).get("first_fill")
        last_fill = (fill_summary or {}).get("last_fill")

        print("=== NG RUNTIME GOVERNANCE STATISTICS V1 ===")
        print(f"symbol={SYMBOL}")
        print()

        print("SUMMARY")
        print(f"source=analytics_closed_trades_v1")
        print(f"fills={int((fill_summary or {}).get('fills') or 0)}")
        print(f"signal_links={len(signal_links)}")
        print(f"closed_trades={len(closed)}")
        print(f"open_qty={round(open_qty, 6)}")
        print(f"first_fill={first_fill}")
        print(f"last_fill={last_fill}")
        print()

        pnls = [x["pnl_points"] for x in closed]
        wins = [x for x in pnls if x > 0]
        losses = [x for x in pnls if x < 0]

        print_perf_block("PERFORMANCE_ALL", closed)

        single_qty_trades = [x for x in closed if abs(float(x.get("qty") or 0.0) - 1.0) < 1e-9]
        batch_trades = [x for x in closed if float(x.get("qty") or 0.0) > 1.0]
        no_batch_trades = [x for x in closed if float(x.get("qty") or 0.0) <= 1.0]

        print_perf_block("PERFORMANCE_WITHOUT_BATCH_QTY_GT_1", no_batch_trades)
        print_perf_block("PERFORMANCE_QTY_EQ_1", single_qty_trades)
        single_exit_trades = [
            x for x in closed
            if not bool((x.get("raw") or {}).get("exit_batch_is_batch"))
        ]
        batch_exit_trades = [
            x for x in closed
            if bool((x.get("raw") or {}).get("exit_batch_is_batch"))
        ]

        print_perf_block("PERFORMANCE_SINGLE_EXIT_TRADES", single_exit_trades)
        print_perf_block("PERFORMANCE_BATCH_EXIT_TRADES", batch_exit_trades)

        print_perf_block("PERFORMANCE_QTY_GT_1", batch_trades)

        by_side = defaultdict(list)
        by_hour = defaultdict(list)
        by_session = defaultdict(list)

        for tr in closed:
            by_side[tr["side"]].append(tr["pnl_points"])
            by_hour[tr["hour_msk"]].append(tr["pnl_points"])
            by_session[tr["session"]].append(tr["pnl_points"])

        print("BY_SIDE")
        for side, arr in sorted(by_side.items()):
            w = [x for x in arr if x > 0]
            l = [x for x in arr if x < 0]
            print(
                f"side={side} trades={len(arr)} pnl={round(sum(arr), 6)} "
                f"winrate={round(len(w)/len(arr), 6) if arr else None} "
                f"expectancy={round(sum(arr)/len(arr), 6) if arr else None} "
                f"profit_factor={safe_pf(w, l)}"
            )
        print()

        print("BY_HOUR_MSK")
        for hour, arr in sorted(by_hour.items()):
            w = [x for x in arr if x > 0]
            l = [x for x in arr if x < 0]
            print(
                f"hour_msk={hour} trades={len(arr)} pnl={round(sum(arr), 6)} "
                f"winrate={round(len(w)/len(arr), 6) if arr else None} "
                f"expectancy={round(sum(arr)/len(arr), 6) if arr else None} "
                f"profit_factor={safe_pf(w, l)}"
            )
        print()

        print("BY_SESSION")
        for sess, arr in sorted(by_session.items()):
            w = [x for x in arr if x > 0]
            l = [x for x in arr if x < 0]
            print(
                f"session={sess} trades={len(arr)} pnl={round(sum(arr), 6)} "
                f"winrate={round(len(w)/len(arr), 6) if arr else None} "
                f"expectancy={round(sum(arr)/len(arr), 6) if arr else None} "
                f"profit_factor={safe_pf(w, l)}"
            )
        print()

        print("RECENT_CLOSED_TRADES")
        for tr in closed[-20:]:
            print(
                f"exit_msk={tr['exit_ts'].astimezone(MSK) if tr['exit_ts'] else None} "
                f"side={tr['side']} qty={tr['qty']} "
                f"entry={round(tr['entry_price'], 6)} exit={round(tr['exit_price'], 6)} "
                f"pnl_points={round(tr['pnl_points'], 6)} session={tr['session']}"
            )
        print()

        print("BLOCK_REASONS")
        print("source_not_available_in_materialized_mode")
        print()

        print("VERDICT")
        if len(closed) < 30:
            print("status=INSUFFICIENT_SAMPLE")
            print("reason=closed_trades_below_30")
        elif len(closed) < 100:
            print("status=EARLY_SAMPLE")
            print("reason=closed_trades_below_100")
        else:
            print("status=ENOUGH_FOR_PRIMARY_EDGE_CHECK")
            print("reason=closed_trades_at_least_100")

        return 0

    with psycopg.connect(db, row_factory=dict_row) as conn:
        fills = conn.execute(
            """
            SELECT fill_id, ts, symbol, side, qty, price, COALESCE(commission, 0) AS commission
            FROM fills
            WHERE symbol = %s
            ORDER BY ts, fill_id
            """,
            (SYMBOL,),
        ).fetchall()

        signal_links = conn.execute(
            """
            SELECT signal_id, fill_id, symbol, side, qty, price, created_at
            FROM signal_fills
            WHERE symbol = %s
            ORDER BY created_at
            """,
            (SYMBOL,),
        ).fetchall()

        block_rows = []
        try:
            block_rows = conn.execute(
                """
                SELECT
                    symbol,
                    block_type,
                    block_reason,
                    strategy,
                    timeframe,
                    created_at
                FROM runtime_guard_pre_signal_block_audit_v1
                WHERE symbol = %s
                ORDER BY created_at DESC
                LIMIT 500
                """,
                (SYMBOL,),
            ).fetchall()
        except Exception:
            block_rows = []

    open_qty = 0.0
    avg_price = 0.0
    entry_ts = None
    entry_side = None
    closed = []

    for f in fills:
        side = str(f["side"]).upper()
        qty = float(f["qty"] or 0.0)
        price = float(f["price"] or 0.0)
        ts = f["ts"]

        if qty <= 0:
            continue

        signed = qty if side == "BUY" else -qty

        if open_qty == 0:
            open_qty = signed
            avg_price = price
            entry_ts = ts
            entry_side = "LONG" if signed > 0 else "SHORT"
            continue

        same_direction = (open_qty > 0 and signed > 0) or (open_qty < 0 and signed < 0)

        if same_direction:
            new_abs = abs(open_qty) + abs(signed)
            avg_price = ((avg_price * abs(open_qty)) + (price * abs(signed))) / new_abs
            open_qty += signed
            continue

        closing_qty = min(abs(open_qty), abs(signed))
        if open_qty > 0:
            pnl = (price - avg_price) * closing_qty
            close_side = "SELL"
        else:
            pnl = (avg_price - price) * closing_qty
            close_side = "BUY"

        closed.append({
            "entry_ts": entry_ts,
            "exit_ts": ts,
            "side": entry_side,
            "close_side": close_side,
            "qty": closing_qty,
            "entry_price": avg_price,
            "exit_price": price,
            "pnl_points": pnl,
            "hour_msk": msk_hour(ts),
            "session": session_ru(msk_hour(ts)),
        })

        remaining = abs(open_qty) - closing_qty
        if remaining <= 1e-9:
            open_qty = 0.0
            avg_price = 0.0
            entry_ts = None
            entry_side = None
        else:
            open_qty = (1 if open_qty > 0 else -1) * remaining

        residual = abs(signed) - closing_qty
        if residual > 1e-9:
            open_qty = (1 if signed > 0 else -1) * residual
            avg_price = price
            entry_ts = ts
            entry_side = "LONG" if open_qty > 0 else "SHORT"

    pnls = [x["pnl_points"] for x in closed]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]

    print("=== NG RUNTIME GOVERNANCE STATISTICS V1 ===")
    print(f"symbol={SYMBOL}")
    print()

    print("SUMMARY")
    print(f"fills={len(fills)}")
    print(f"signal_links={len(signal_links)}")
    print(f"closed_trades={len(closed)}")
    print(f"open_qty={round(open_qty, 6)}")
    print(f"first_fill={fills[0]['ts'] if fills else None}")
    print(f"last_fill={fills[-1]['ts'] if fills else None}")
    print()

    print_perf_block("PERFORMANCE_ALL", closed)

    # Русский комментарий: batch-сделки qty > 1 могут искажать первичную оценку edge.
    single_qty_trades = [x for x in closed if abs(float(x.get("qty") or 0.0) - 1.0) < 1e-9]
    batch_trades = [x for x in closed if float(x.get("qty") or 0.0) > 1.0]
    no_batch_trades = [x for x in closed if float(x.get("qty") or 0.0) <= 1.0]

    print_perf_block("PERFORMANCE_WITHOUT_BATCH_QTY_GT_1", no_batch_trades)
    print_perf_block("PERFORMANCE_QTY_EQ_1", single_qty_trades)
    print_perf_block("PERFORMANCE_QTY_GT_1", batch_trades)

    by_side = defaultdict(list)
    by_hour = defaultdict(list)
    by_session = defaultdict(list)

    for tr in closed:
        by_side[tr["side"]].append(tr["pnl_points"])
        by_hour[tr["hour_msk"]].append(tr["pnl_points"])
        by_session[tr["session"]].append(tr["pnl_points"])

    print("BY_SIDE")
    for side, arr in sorted(by_side.items()):
        w = [x for x in arr if x > 0]
        l = [x for x in arr if x < 0]
        print(
            f"side={side} trades={len(arr)} pnl={round(sum(arr), 6)} "
            f"winrate={round(len(w)/len(arr), 6) if arr else None} "
            f"expectancy={round(sum(arr)/len(arr), 6) if arr else None} "
            f"profit_factor={safe_pf(w, l)}"
        )
    print()

    print("BY_HOUR_MSK")
    for hour, arr in sorted(by_hour.items()):
        w = [x for x in arr if x > 0]
        l = [x for x in arr if x < 0]
        print(
            f"hour_msk={hour} trades={len(arr)} pnl={round(sum(arr), 6)} "
            f"winrate={round(len(w)/len(arr), 6) if arr else None} "
            f"expectancy={round(sum(arr)/len(arr), 6) if arr else None} "
            f"profit_factor={safe_pf(w, l)}"
        )
    print()

    print("BY_SESSION")
    for sess, arr in sorted(by_session.items()):
        w = [x for x in arr if x > 0]
        l = [x for x in arr if x < 0]
        print(
            f"session={sess} trades={len(arr)} pnl={round(sum(arr), 6)} "
            f"winrate={round(len(w)/len(arr), 6) if arr else None} "
            f"expectancy={round(sum(arr)/len(arr), 6) if arr else None} "
            f"profit_factor={safe_pf(w, l)}"
        )
    print()

    print("RECENT_CLOSED_TRADES")
    for tr in closed[-20:]:
        print(
            f"exit_msk={tr['exit_ts'].astimezone(MSK) if tr['exit_ts'] else None} "
            f"side={tr['side']} qty={tr['qty']} "
            f"entry={round(tr['entry_price'], 6)} exit={round(tr['exit_price'], 6)} "
            f"pnl_points={round(tr['pnl_points'], 6)} session={tr['session']}"
        )
    print()

    print("BLOCK_REASONS")
    if not block_rows:
        print("no_runtime_guard_pre_signal_block_rows")
    else:
        counts = defaultdict(int)
        for r in block_rows:
            key = (r.get("block_type"), r.get("block_reason"))
            counts[key] += 1
        for (block_type, reason), count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"block_type={block_type} reason={reason} count={count}")

    print()
    print("VERDICT")
    if len(closed) < 30:
        print("status=INSUFFICIENT_SAMPLE")
        print("reason=closed_trades_below_30")
    elif len(closed) < 100:
        print("status=EARLY_SAMPLE")
        print("reason=closed_trades_below_100")
    else:
        print("status=ENOUGH_FOR_PRIMARY_EDGE_CHECK")
        print("reason=closed_trades_at_least_100")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
