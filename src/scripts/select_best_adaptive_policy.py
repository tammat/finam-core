from __future__ import annotations

import argparse

from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=20)
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
        print("АДАПТИВНАЯ_ПОЛИТИКА_ПУСТО", flush=True)
        return 0

    best = None

    for r in rows:
        report_id = str(r[0])

        variants = [
            {
                "mode": "BASE",
                "net_pnl": float(r[1]),
                "expectancy": float(r[4]),
                "winrate": float(r[7]),
            },
            {
                "mode": "LIMITED",
                "net_pnl": float(r[2]),
                "expectancy": float(r[5]),
                "winrate": float(r[8]),
            },
            {
                "mode": "SELECTIVE",
                "net_pnl": float(r[3]),
                "expectancy": float(r[6]),
                "winrate": float(r[9]),
            },
        ]

        for v in variants:
            score = (
                v["expectancy"] * 1.0
                + v["winrate"] * 10.0
                + max(0.0, v["net_pnl"]) * 0.01
            )

            candidate = {
                "report_id": report_id,
                "mode": v["mode"],
                "score": score,
                **v,
            }

            if best is None or candidate["score"] > best["score"]:
                best = candidate

    print(
        "ЛУЧШАЯ_АДАПТИВНАЯ_ПОЛИТИКА "
        f"report_id={best['report_id']} "
        f"mode={best['mode']} "
        f"score={best['score']:.6f} "
        f"net_pnl={best['net_pnl']:.6f} "
        f"expectancy={best['expectancy']:.6f} "
        f"winrate={best['winrate']:.4f}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
