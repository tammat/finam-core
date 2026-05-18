from __future__ import annotations

import argparse
from datetime import datetime, timezone

from finam_core.research.policy_decision_repository import PolicyDecisionRepository
from finam_core.storage.postgres_logger import PostgresLogger

def score_policy(v: dict, objective: str) -> float:
    if objective == "profit":
        return v["net_pnl"]
    if objective == "risk":
        return v["winrate"] * 100.0 + v["expectancy"] * 0.25
    if objective == "conservative":
        mode_bonus = 5.0 if v["mode"] == "SELECTIVE" else 0.0
        mode_penalty = -5.0 if v["mode"] == "BASE" else 0.0
        return (
            v["expectancy"] * 1.0
            + v["winrate"] * 20.0
            + max(0.0, v["net_pnl"]) * 0.002
            + mode_bonus
            + mode_penalty
        )
    return (
        v["expectancy"] * 1.0
        + v["winrate"] * 10.0
        + max(0.0, v["net_pnl"]) * 0.01
    )


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--objective", choices=("profit", "balanced", "conservative", "risk"), required=True)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--decision-id", default="")
    p.add_argument("--active", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    sql = """
    select
        report_id,
        base_net_pnl,
        limited_net_pnl,
        selective_net_pnl,
        base_expectancy,
        limited_expectancy,
        selective_expectancy,
        base_winrate,
        limited_winrate,
        selective_winrate,
        created_at
    from research_policy_impact_reports
    order by created_at desc, id desc
    limit %s
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.limit,))
            rows = cur.fetchall()

    if not rows:
        print("POLICY_DECISION_EMPTY", flush=True)
        return 0

    best = None

    for r in rows:
        report_id = str(r[0])
        variants = [
            {"mode": "BASE", "net_pnl": float(r[1]), "expectancy": float(r[4]), "winrate": float(r[7])},
            {"mode": "LIMITED", "net_pnl": float(r[2]), "expectancy": float(r[5]), "winrate": float(r[8])},
            {"mode": "SELECTIVE", "net_pnl": float(r[3]), "expectancy": float(r[6]), "winrate": float(r[9])},
        ]

        for v in variants:
            score = score_policy(v, args.objective)
            candidate = {
                "decision_id": args.decision_id or f"policy-decision-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
                "report_id": report_id,
                "objective": args.objective,
                "mode": v["mode"],
                "score": round(score, 6),
                **v,
            }

            if best is None or candidate["score"] > best["score"]:
                best = candidate

    with pg._connect() as conn:
        saved = PolicyDecisionRepository(conn).save_decision(
            decision=best,
            active=args.active,
        )

    print(
        "POLICY_DECISION_SAVED "
        f"decision_id={best['decision_id']} "
        f"objective={best['objective']} "
        f"mode={best['mode']} "
        f"score={best['score']:.6f} "
        f"active={args.active} "
        f"rows={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
