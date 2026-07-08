from __future__ import annotations

import json
from decimal import Decimal

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MAX_EDGE_SCORE_AUDIT_V1"


def d(v) -> Decimal:
    return Decimal(str(v or 0))


def corr(xs: list[Decimal], ys: list[Decimal]) -> Decimal:
    n = len(xs)
    if n < 2:
        return Decimal("0")

    mx = sum(xs) / Decimal(n)
    my = sum(ys) / Decimal(n)

    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) * (x - mx) for x in xs)
    vy = sum((y - my) * (y - my) for y in ys)

    if vx == 0 or vy == 0:
        return Decimal("0")

    return (cov / (vx.sqrt() * vy.sqrt())).quantize(Decimal("0.000001"))


def verdict_corr(value: Decimal) -> str:
    if value >= Decimal("0.50"):
        return "PASS"
    if value >= Decimal("0.20"):
        return "WARN"
    return "FAIL"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    symbol,
                    strategy_code,
                    edge_score,
                    confidence,
                    net_after_tax,
                    profit_factor,
                    expectancy,
                    max_drawdown,
                    trades
                FROM analytics.max_edge_ranking_v1
                WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'
                ORDER BY rank_no;
            """)
            rows = [dict(r) for r in cur.fetchall()]

            scores = [d(r["edge_score"]) for r in rows]
            net = [d(r["net_after_tax"]) for r in rows]
            pf = [d(r["profit_factor"]) for r in rows]
            exp = [d(r["expectancy"]) for r in rows]
            dd = [abs(d(r["max_drawdown"])) for r in rows]

            metrics: list[tuple[str, Decimal, str, dict]] = []

            c_net = corr(scores, net)
            metrics.append(("CORR_SCORE_NET_AFTER_TAX", c_net, verdict_corr(c_net), {"rows": len(rows)}))

            c_pf = corr(scores, pf)
            metrics.append(("CORR_SCORE_PROFIT_FACTOR", c_pf, verdict_corr(c_pf), {"rows": len(rows)}))

            c_exp = corr(scores, exp)
            metrics.append(("CORR_SCORE_EXPECTANCY", c_exp, verdict_corr(c_exp), {"rows": len(rows)}))

            c_dd = corr(scores, dd)
            metrics.append((
                "CORR_SCORE_DRAWDOWN_ABS",
                c_dd,
                "PASS" if c_dd <= Decimal("0.20") else "WARN",
                {"rows": len(rows), "expected": "low_or_negative"},
            ))

            outliers = [
                r for r in rows
                if d(r["edge_score"]) >= Decimal("80") and int(r["trades"] or 0) < 30
            ]
            metrics.append((
                "HIGH_SCORE_LOW_SAMPLE_OUTLIERS",
                Decimal(len(outliers)),
                "PASS" if len(outliers) == 0 else "FAIL",
                {"outliers": [{"symbol": r["symbol"], "score": str(r["edge_score"]), "trades": r["trades"]} for r in outliers]},
            ))

            low_sample_rows = [r for r in rows if int(r["trades"] or 0) < 30]
            metrics.append((
                "LOW_SAMPLE_ROWS",
                Decimal(len(low_sample_rows)),
                "PASS" if len(low_sample_rows) == 0 else "WARN",
                {
                    "rows": [
                        {
                            "symbol": r["symbol"],
                            "score": str(r["edge_score"]),
                            "trades": r["trades"],
                        }
                        for r in low_sample_rows[:20]
                    ]
                },
            ))

            fail_count = sum(1 for _, _, v, _ in metrics if v == "FAIL")
            warn_count = sum(1 for _, _, v, _ in metrics if v == "WARN")
            overall = "PASS" if fail_count == 0 and warn_count <= 2 else ("WARN" if fail_count == 0 else "FAIL")

            metrics.append((
                "OVERALL",
                Decimal(fail_count),
                overall,
                {"fail_count": fail_count, "warn_count": warn_count, "metric_count": len(metrics)},
            ))

            for metric_code, metric_value, verdict, details in metrics:
                cur.execute("""
                    INSERT INTO analytics.max_edge_score_audit_metric_v1
                    (metric_code, metric_value, verdict, details, source_version)
                    VALUES (%s,%s,%s,%s,%s);
                """, (
                    metric_code,
                    metric_value,
                    verdict,
                    json.dumps(details, ensure_ascii=False),
                    SOURCE_VERSION,
                ))

    print("=== MAX_EDGE_SCORE_AUDIT_PART2 ===")
    for metric_code, metric_value, verdict, _ in metrics:
        print(f"METRIC {metric_code}={metric_value} verdict={verdict}")
    print(f"OVERALL={overall}")
    print("VERDICT=MAX_EDGE_SCORE_AUDIT_PART2_READY")


if __name__ == "__main__":
    main()
