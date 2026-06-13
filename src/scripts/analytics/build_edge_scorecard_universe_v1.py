#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
from collections import defaultdict
import psycopg
from psycopg.rows import dict_row


def pf(pnls: list[float]):
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    if gl == 0:
        return None if gp == 0 else "inf"
    return gp / gl


def stats(rows: list[dict]) -> dict:
    pnls = [float(r["pnl_points"] or 0.0) for r in rows]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    n = len(pnls)
    pf_value = pf(pnls)
    return {
        "trades": n,
        "pnl": sum(pnls),
        "winrate": len(wins) / n if n else None,
        "expectancy": sum(pnls) / n if n else None,
        "profit_factor": pf_value,
        "wins": len(wins),
        "losses": len(losses),
    }


def classify(s: dict) -> tuple[str, str]:
    trades = int(s["trades"] or 0)
    exp = s["expectancy"]
    pfv = s["profit_factor"]
    top1_day_share = s.get("top1_day_share")
    top3_day_share = s.get("top3_day_share")

    if trades < 30:
        return "RESEARCH_ONLY", "sample_below_30"
    if exp is None or exp <= 0:
        return "REJECT", "non_positive_expectancy"
    if pfv is None or pfv == "inf":
        return "RESEARCH_ONLY", "profit_factor_unstable"
    if pfv < 1.10:
        return "REJECT", "profit_factor_below_1_10"

    if top1_day_share is not None and top1_day_share > 0.30:
        return "RESEARCH_ONLY", "profit_concentration_top1_day"
    if top3_day_share is not None and top3_day_share > 0.60:
        return "RESEARCH_ONLY", "profit_concentration_top3_days"

    if trades >= 100 and pfv >= 1.30 and exp > 0:
        return "PROMOTABLE_CANDIDATE", "sample_and_edge_pass"
    if pfv >= 1.20 and exp > 0:
        return "SHADOW_CANDIDATE", "positive_edge_needs_more_validation"
    return "RESEARCH_ONLY", "weak_positive_edge"


def fmt(x, digits=6):
    if x is None:
        return "None"
    if x == "inf":
        return "inf"
    return f"{float(x):.{digits}f}"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", default=os.getenv("SYMBOLS", ""))
    p.add_argument("--symbol-pattern", default=os.getenv("SYMBOL_PATTERN", ""))
    p.add_argument("--min-trades", type=int, default=int(os.getenv("MIN_TRADES", "1")))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    db = os.getenv("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL is required")

    params = []
    where = ["1=1"]

    if args.symbols:
        symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
        where.append("symbol = ANY(%s)")
        params.append(symbols)

    if args.symbol_pattern:
        where.append("symbol ~ %s")
        params.append(args.symbol_pattern)

    sql = f"""
        SELECT
            symbol,
            strategy,
            side,
            qty,
            exit_ts,
            pnl_points,
            hour_msk,
            weekday,
            session,
            raw
        FROM analytics_closed_trades_v1
        WHERE {' AND '.join(where)}
        ORDER BY symbol, strategy, exit_ts
    """

    with psycopg.connect(db, row_factory=dict_row) as conn:
        rows = list(conn.execute(sql, tuple(params)))

    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["symbol"], r["strategy"])].append(r)

    score_rows = []
    for (symbol, strategy), arr in grouped.items():
        s = stats(arr)
        if s["trades"] < args.min_trades:
            continue

        by_date = defaultdict(float)
        for r in arr:
            exit_ts = r.get("exit_ts")
            if exit_ts is None:
                continue
            d = exit_ts.astimezone().date().isoformat()
            by_date[d] += float(r["pnl_points"] or 0.0)

        date_pnls = sorted(by_date.values(), reverse=True)
        total_pnl = float(s["pnl"] or 0.0)
        top1_day_share = date_pnls[0] / total_pnl if date_pnls and abs(total_pnl) > 1e-12 else None
        top3_day_share = sum(date_pnls[:3]) / total_pnl if date_pnls and abs(total_pnl) > 1e-12 else None

        s["top1_day_share"] = top1_day_share
        s["top3_day_share"] = top3_day_share

        verdict, reason = classify(s)

        batch_rows = [
            r for r in arr
            if bool((r.get("raw") or {}).get("exit_batch_is_batch"))
        ]
        batch_pnl = sum(float(r["pnl_points"] or 0.0) for r in batch_rows)
        batch_share = batch_pnl / s["pnl"] if abs(s["pnl"]) > 1e-12 else None

        score_rows.append({
            "symbol": symbol,
            "strategy": strategy,
            **s,
            "batch_trades": len(batch_rows),
            "batch_pnl": batch_pnl,
            "batch_pnl_share": batch_share,
            "top1_day_share": top1_day_share,
            "top3_day_share": top3_day_share,
            "verdict": verdict,
            "reason": reason,
        })

    score_rows.sort(
        key=lambda r: (
            0 if r["expectancy"] is None else r["expectancy"],
            0 if r["profit_factor"] in (None, "inf") else float(r["profit_factor"]),
            r["trades"],
        ),
        reverse=True,
    )

    print("=== EDGE SCORECARD UNIVERSE V1 ===")
    print(f"rows={len(score_rows)}")
    print(f"min_trades={args.min_trades}")
    print()

    print("RANKING")
    print(
        "rank symbol strategy trades pnl expectancy profit_factor "
        "winrate batch_trades batch_pnl_share top1_day_share top3_day_share verdict reason"
    )

    for i, r in enumerate(score_rows, 1):
        print(
            f"{i} "
            f"{r['symbol']} "
            f"{r['strategy']} "
            f"{r['trades']} "
            f"{fmt(r['pnl'])} "
            f"{fmt(r['expectancy'])} "
            f"{fmt(r['profit_factor'])} "
            f"{fmt(r['winrate'])} "
            f"{r['batch_trades']} "
            f"{fmt(r['batch_pnl_share'])} "
            f"{fmt(r['top1_day_share'])} "
            f"{fmt(r['top3_day_share'])} "
            f"{r['verdict']} "
            f"{r['reason']}"
        )

    print()
    print("FINAL_SUMMARY")
    counts = defaultdict(int)
    for r in score_rows:
        counts[r["verdict"]] += 1

    for verdict in sorted(counts):
        print(f"{verdict}={counts[verdict]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
