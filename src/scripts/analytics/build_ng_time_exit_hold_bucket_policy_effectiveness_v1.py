#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

from finam_core.governance.ng_time_exit_hold_bucket_policy_v1 import (
    NgTimeExitHoldBucketPolicyV1,
)

NG_TRUSTED_FROM = "2026-06-03 00:00:00+00"
SOURCE = "closed_trade_engine_v1_1"


def pf(gp: float, gl: float) -> str:
    if gl == 0:
        return "None"
    return f"{gp / abs(gl):.6f}"


def calc(rows, mode: str) -> dict:
    out = {
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "net_pnl": 0.0,
    }

    for r in rows:
        pnl = float(r["net_pnl"] or 0.0)

        if mode == "policy":
            pnl = float(r["policy_pnl"] or 0.0)

        out["trades"] += 1
        out["net_pnl"] += pnl

        if pnl > 0:
            out["wins"] += 1
            out["gross_profit"] += pnl
        elif pnl < 0:
            out["losses"] += 1
            out["gross_loss"] += pnl

    out["expectancy"] = out["net_pnl"] / out["trades"] if out["trades"] else 0.0
    out["winrate"] = out["wins"] / out["trades"] if out["trades"] else 0.0
    out["profit_factor"] = pf(out["gross_profit"], out["gross_loss"])
    return out


def main() -> None:
    print("=== NG TIME EXIT HOLD BUCKET POLICY EFFECTIVENESS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("scope=trusted_time_exit_only")
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
                    net_pnl::float AS net_pnl,
                    COALESCE(hold_seconds, holding_seconds, 0)::float AS hold_seconds,
                    COALESCE(NULLIF(payload->>'exit_reason', ''), 'NO_MATCH') AS exit_reason,
                    COALESCE(exit_ts, closed_at, created_at) AS ts
                FROM closed_trades
                WHERE source = %s
                  AND symbol LIKE 'NG%%'
                  AND COALESCE(NULLIF(payload->>'exit_reason', ''), 'NO_MATCH') = 'time_exit'
                  AND COALESCE(exit_ts, closed_at, created_at) >= %s
                ORDER BY COALESCE(exit_ts, closed_at, created_at), id
            """, (SOURCE, NG_TRUSTED_FROM))
            rows = cur.fetchall()

    policy = NgTimeExitHoldBucketPolicyV1()
    enriched = []

    for r in rows:
        pnl = float(r["net_pnl"] or 0.0)
        hold_seconds = float(r["hold_seconds"] or 0.0)

        decision = policy.evaluate(
            root_symbol="NG",
            exit_reason=str(r["exit_reason"]),
            hold_seconds=hold_seconds,
            unrealized_pnl=pnl,
        )

        policy_pnl = pnl
        if not decision.allowed and decision.action == "EXTEND_HOLD":
            # Proxy: если отрицательный early time_exit заблокирован,
            # фиксируем текущий эффект как 0 вместо фактического убытка.
            policy_pnl = 0.0

        rr = dict(r)
        rr["policy_allowed"] = decision.allowed
        rr["policy_action"] = decision.action
        rr["policy_reason"] = decision.reason
        rr["policy_pnl"] = policy_pnl
        enriched.append(rr)

    current = calc(enriched, "current")
    governed = calc(enriched, "policy")

    blocked = [r for r in enriched if not r["policy_allowed"]]
    allowed = [r for r in enriched if r["policy_allowed"]]

    print("POLICY_ACTION_SUMMARY")
    print(f"ACTION_ROW action=ALLOW rows={len(allowed)}")
    print(f"ACTION_ROW action=EXTEND_HOLD rows={len(blocked)}")
    print()

    print("EFFECTIVENESS")
    print(
        "CURRENT_ROW "
        f"trades={current['trades']} wins={current['wins']} losses={current['losses']} "
        f"winrate={current['winrate']:.6f} "
        f"gross_profit={current['gross_profit']:.6f} "
        f"gross_loss={current['gross_loss']:.6f} "
        f"net_pnl={current['net_pnl']:.6f} "
        f"expectancy={current['expectancy']:.6f} "
        f"profit_factor={current['profit_factor']}"
    )
    print(
        "POLICY_ROW "
        f"trades={governed['trades']} wins={governed['wins']} losses={governed['losses']} "
        f"winrate={governed['winrate']:.6f} "
        f"gross_profit={governed['gross_profit']:.6f} "
        f"gross_loss={governed['gross_loss']:.6f} "
        f"net_pnl={governed['net_pnl']:.6f} "
        f"expectancy={governed['expectancy']:.6f} "
        f"profit_factor={governed['profit_factor']}"
    )
    print(
        "DELTA_ROW "
        f"delta_net_pnl={(governed['net_pnl'] - current['net_pnl']):.6f} "
        f"delta_expectancy={(governed['expectancy'] - current['expectancy']):.6f}"
    )
    print()

    print("BLOCKED_SAMPLE")
    for r in blocked[:30]:
        print(
            f"BLOCKED_ROW id={r['id']} symbol={r['symbol']} side={r['side']} "
            f"hold_seconds={float(r['hold_seconds'] or 0):.2f} "
            f"net_pnl={float(r['net_pnl'] or 0):.6f} "
            f"policy_action={r['policy_action']} "
            f"policy_reason={r['policy_reason']} "
            f"ts={r['ts']}"
        )
    if not blocked:
        print("NONE")
    print()

    print("SUMMARY")
    print(f"TRUSTED_TIME_EXIT_ROWS={len(enriched)}")
    print(f"EXTEND_HOLD_ROWS={len(blocked)}")
    if governed["net_pnl"] > current["net_pnl"]:
        verdict = "NG_HOLD_BUCKET_POLICY_SUPPORTED"
    else:
        verdict = "NG_HOLD_BUCKET_POLICY_NOT_SUPPORTED"
    print(f"VERDICT={verdict}")
    print("NG_TIME_EXIT_HOLD_BUCKET_POLICY_EFFECTIVENESS_V1_OK")


if __name__ == "__main__":
    main()
