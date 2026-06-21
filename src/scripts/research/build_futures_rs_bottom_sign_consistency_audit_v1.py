#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


def dec(v):
    return Decimal(str(v)) if v is not None else Decimal("0")


def pct(source, future):
    source = dec(source)
    future = dec(future)
    if source == 0:
        return None
    return (future - source) / source * Decimal("100")


def sign(v):
    if v is None:
        return 0
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    opposite = 0
    same = 0
    checked = 0
    sample_rows = []

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    selection,
                    horizon_min,
                    observations,
                    avg_return_pct,
                    profit_factor
                from analytics_futures_rs_historical_scorecard_v1
                where selection in ('BOTTOM1','BOTTOM3')
                order by selection, horizon_min
            """)
            hist = cur.fetchall()

            cur.execute("""
                select
                    selection,
                    filter_name,
                    horizon_min,
                    observations,
                    avg_return_pct,
                    profit_factor
                from analytics_futures_rs_bottom_reversal_filters_v1
                where selection in ('BOTTOM1','BOTTOM3')
                  and filter_name = 'ALL'
                order by selection, horizon_min
            """)
            filt = cur.fetchall()

            hist_map = {(r["selection"], r["horizon_min"]): r for r in hist}
            filt_map = {(r["selection"], r["horizon_min"]): r for r in filt}

            for key, h in hist_map.items():
                f = filt_map.get(key)
                if not f:
                    continue

                hist_avg = dec(h["avg_return_pct"])
                filt_avg = dec(f["avg_return_pct"])

                if sign(hist_avg) == sign(filt_avg):
                    same += 1
                else:
                    opposite += 1

                checked += 1
                sample_rows.append((key[0], key[1], h, f, hist_avg, filt_avg))

    print("=== FUTURES_RS_BOTTOM_SIGN_CONSISTENCY_AUDIT_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")
    print(f"checked_pairs={checked}")
    print(f"same_sign_count={same}")
    print(f"opposite_sign_count={opposite}")

    selection_mismatch = 0

    for selection, horizon, h, f, hist_avg, filt_avg in sample_rows:
        h_obs = int(h["observations"])
        f_obs = int(f["observations"])
        diff_pct = abs(h_obs - f_obs) / max(h_obs, 1) * 100

        if diff_pct > 2:
            selection_mismatch += 1

        print(
            "SIGN_AUDIT_ROW "
            f"selection={selection} "
            f"horizon_min={horizon} "
            f"hist_observations={h_obs} "
            f"filter_observations={f_obs} "
            f"obs_diff_pct={diff_pct:.4f} "
            f"hist_avg_return_pct={hist_avg} "
            f"filter_avg_return_pct={filt_avg} "
            f"hist_profit_factor={h['profit_factor']} "
            f"filter_profit_factor={f['profit_factor']} "
            f"same_sign={int(sign(hist_avg) == sign(filt_avg))}",
            flush=True,
        )

    print(f"selection_mismatch_count={selection_mismatch}")

    if opposite > 0:
        verdict = "SIGN_BUG_CONFIRMED"
    elif selection_mismatch > 0:
        verdict = "SELECTION_MISMATCH"
    else:
        verdict = "SIGN_CONSISTENCY_OK"

    print(f"VERDICT={verdict}")
    print("TEST_FUTURES_RS_BOTTOM_SIGN_CONSISTENCY_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
