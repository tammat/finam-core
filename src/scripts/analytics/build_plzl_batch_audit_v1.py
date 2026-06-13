#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from collections import defaultdict
from statistics import median

import psycopg
from psycopg.rows import dict_row


SYMBOL = os.getenv("SYMBOL", "PLZL@MISX")


def fmt(x, digits=6):
    if x is None:
        return "None"
    return f"{float(x):.{digits}f}"


def main() -> int:
    db = os.getenv("DATABASE_URL")
    if not db:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(db, row_factory=dict_row) as conn:
        rows = list(conn.execute(
            """
            SELECT
                trade_id,
                symbol,
                strategy,
                qty,
                pnl_points,
                raw,
                exit_ts
            FROM analytics_closed_trades_v1
            WHERE symbol = %s
            ORDER BY exit_ts, trade_id
            """,
            (SYMBOL,),
        ))

    total_trades = len(rows)
    total_pnl = sum(float(r["pnl_points"] or 0.0) for r in rows)

    batch_rows = [
        r for r in rows
        if bool((r.get("raw") or {}).get("exit_batch_is_batch"))
    ]
    batch_trades = len(batch_rows)
    batch_pnl = sum(float(r["pnl_points"] or 0.0) for r in batch_rows)

    batches = defaultdict(list)
    for r in rows:
        raw = r.get("raw") or {}
        key = raw.get("exit_batch_key") or r["trade_id"]
        batches[str(key)].append(r)

    batch_groups = []
    for key, arr in batches.items():
        size = len(arr)
        pnl = sum(float(r["pnl_points"] or 0.0) for r in arr)
        batch_groups.append({
            "key": key,
            "size": size,
            "pnl": pnl,
            "is_batch": size > 1,
        })

    batch_groups_sorted = sorted(batch_groups, key=lambda x: x["pnl"], reverse=True)
    batch_sizes = [g["size"] for g in batch_groups if g["is_batch"]]

    top1_pnl = batch_groups_sorted[0]["pnl"] if batch_groups_sorted else 0.0
    top5_pnl = sum(g["pnl"] for g in batch_groups_sorted[:5])

    batch_share = batch_trades / total_trades if total_trades else 0.0
    batch_pnl_share = batch_pnl / total_pnl if abs(total_pnl) > 1e-12 else None
    top1_batch_share = top1_pnl / total_pnl if abs(total_pnl) > 1e-12 else None
    top5_batch_share = top5_pnl / total_pnl if abs(total_pnl) > 1e-12 else None

    flags = []
    if batch_share > 0.50:
        flags.append("BATCH_TRADE_SHARE_GT_50")
    if batch_pnl_share is not None and batch_pnl_share > 0.50:
        flags.append("BATCH_PNL_SHARE_GT_50")
    if top1_batch_share is not None and top1_batch_share > 0.20:
        flags.append("TOP1_BATCH_SHARE_GT_20")
    if top5_batch_share is not None and top5_batch_share > 0.50:
        flags.append("TOP5_BATCH_SHARE_GT_50")
    if batch_sizes and max(batch_sizes) >= 20:
        flags.append("MEGA_BATCH")

    if "BATCH_PNL_SHARE_GT_50" in flags or "TOP5_BATCH_SHARE_GT_50" in flags:
        verdict = "EDGE_BATCH_DEPENDENT"
    elif flags:
        verdict = "EDGE_PARTIALLY_BATCH_DEPENDENT"
    else:
        verdict = "EDGE_BATCH_INDEPENDENT"

    print("=== PLZL BATCH AUDIT V1 ===")
    print(f"symbol={SYMBOL}")
    print()

    print("SUMMARY")
    print(f"closed_trades={total_trades}")
    print(f"batch_trades={batch_trades}")
    print(f"batch_share={fmt(batch_share)}")
    print(f"batch_groups={sum(1 for g in batch_groups if g['is_batch'])}")
    print()

    print("PNL")
    print(f"total_pnl={fmt(total_pnl)}")
    print(f"batch_pnl={fmt(batch_pnl)}")
    print(f"batch_pnl_share={fmt(batch_pnl_share)}")
    print()

    print("TOP_BATCHES")
    print(f"top_1_batch_pnl={fmt(top1_pnl)}")
    print(f"top_1_batch_share={fmt(top1_batch_share)}")
    print(f"top_5_batch_pnl={fmt(top5_pnl)}")
    print(f"top_5_batch_share={fmt(top5_batch_share)}")
    print()

    print("SIZE")
    print(f"avg_batch_size={fmt(sum(batch_sizes) / len(batch_sizes)) if batch_sizes else 'None'}")
    print(f"median_batch_size={fmt(median(batch_sizes)) if batch_sizes else 'None'}")
    print(f"max_batch_size={max(batch_sizes) if batch_sizes else 0}")
    print()

    print("TOP_BATCH_ROWS")
    for g in batch_groups_sorted[:10]:
        print(
            f"batch_key={g['key']} size={g['size']} "
            f"pnl={fmt(g['pnl'])} is_batch={int(g['is_batch'])}"
        )
    print()

    print("VERDICT")
    print(f"status={verdict}")
    print(f"flags={','.join(flags) if flags else 'none'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
