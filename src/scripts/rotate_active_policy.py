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
            v["expectancy"]
            + v["winrate"] * 20.0
            + max(0.0, v["net_pnl"]) * 0.002
            + mode_bonus
            + mode_penalty
        )

    return (
        v["expectancy"]
        + v["winrate"] * 10.0
        + max(0.0, v["net_pnl"]) * 0.01
    )


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--objective", choices=("profit", "balanced", "conservative", "risk"), required=True)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--decision-id", default="")
    p.add_argument("--dry-run", action="store_true")
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
        print(f"POLICY_ROTATION_EMPTY objective={args.objective}", flush=True)
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
            score = round(score_policy(v, args.objective), 6)
            candidate = {
                "decision_id": args.decision_id or (
                    f"auto-policy-{args.objective}-"
                    f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
                ),
                "report_id": report_id,
                "objective": args.objective,
                "mode": v["mode"],
                "score": score,
                **v,
            }

            if best is None or candidate["score"] > best["score"]:
                best = candidate

    print(
        "POLICY_ROTATION_SELECTED "
        f"objective={best['objective']} "
        f"decision_id={best['decision_id']} "
        f"report_id={best['report_id']} "
        f"mode={best['mode']} "
        f"score={best['score']:.6f} "
        f"net_pnl={best['net_pnl']:.6f} "
        f"expectancy={best['expectancy']:.6f} "
        f"winrate={best['winrate']:.4f} "
        f"dry_run={args.dry_run}",
        flush=True,
    )

    if args.dry_run:
        return 0

    with pg._connect() as conn:
        saved = PolicyDecisionRepository(conn).save_decision(
            decision=best,
            active=True,
        )

    print(
        "POLICY_ROTATION_APPLIED "
        f"objective={best['objective']} "
        f"decision_id={best['decision_id']} "
        f"mode={best['mode']} "
        f"rows={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
