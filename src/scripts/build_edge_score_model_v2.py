from __future__ import annotations

from decimal import Decimal
import psycopg2
import psycopg2.extras

SOURCE_VERSION = "EDGE_SCORE_MODEL_V2"


def d(v) -> Decimal:
    return Decimal(str(v or 0))


def clamp(v: Decimal, lo=Decimal("0"), hi=Decimal("100")) -> Decimal:
    return max(lo, min(hi, v)).quantize(Decimal("0.000001"))


def norm_net(v: Decimal) -> Decimal:
    return clamp(Decimal("50") + v)


def norm_pf(v: Decimal) -> Decimal:
    return clamp((v - Decimal("1")) * Decimal("50"))


def norm_expectancy(v: Decimal) -> Decimal:
    return clamp(Decimal("50") + v * Decimal("10"))


def norm_trades(v: Decimal) -> Decimal:
    return clamp(v * Decimal("2"))


def norm_drawdown(v: Decimal) -> Decimal:
    return clamp(Decimal("100") - abs(v))


def weighted(items: list[tuple[Decimal, Decimal]]) -> Decimal:
    total_w = sum(w for _, w in items)
    if total_w <= 0:
        return Decimal("0")
    return clamp(sum(v * w for v, w in items) / total_w)


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT metric_code, weight
                FROM analytics.edge_score_weight_v2
                WHERE enabled=true
                  AND model_code='EDGE_SCORE_V2';
            """)
            weights = {r["metric_code"]: d(r["weight"]) for r in cur.fetchall()}

            cur.execute("""
                SELECT *
                FROM analytics.max_edge_ranking_v1
                WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'
                ORDER BY rank_no;
            """)
            rows = [dict(r) for r in cur.fetchall()]

            cur.execute("DELETE FROM analytics.edge_score_model_v2 WHERE source_version=%s;", (SOURCE_VERSION,))

            for row in rows:
                metrics = {
                    "NET_AFTER_TAX": (d(row["net_after_tax"]), norm_net(d(row["net_after_tax"]))),
                    "PROFIT_FACTOR": (d(row["profit_factor"]), norm_pf(d(row["profit_factor"]))),
                    "EXPECTANCY": (d(row["expectancy"]), norm_expectancy(d(row["expectancy"]))),
                    "TRADES": (d(row["trades"]), norm_trades(d(row["trades"]))),
                    "CONFIDENCE": (d(row["confidence"]), clamp(d(row["confidence"]))),
                    "EXECUTION_DEFAULT": (Decimal("100"), Decimal("100")),
                    "MAX_DRAWDOWN": (d(row["max_drawdown"]), norm_drawdown(d(row["max_drawdown"]))),
                }

                economic = weighted([(metrics[k][1], weights[k]) for k in ("NET_AFTER_TAX", "PROFIT_FACTOR", "EXPECTANCY")])
                reliability = weighted([(metrics[k][1], weights[k]) for k in ("TRADES", "CONFIDENCE")])
                execution = metrics["EXECUTION_DEFAULT"][1]
                risk = metrics["MAX_DRAWDOWN"][1]

                group_scores = {
                    "GROUP_ECONOMIC": economic,
                    "GROUP_RELIABILITY": reliability,
                    "GROUP_EXECUTION": execution,
                    "GROUP_RISK": risk,
                }

                edge_v2 = clamp(
                    sum(
                        value * weights.get(group_code, Decimal("0"))
                        for group_code, value in group_scores.items()
                    )
                )

                cur.execute("""
                    INSERT INTO analytics.edge_score_model_v2 (
                        candidate_id, symbol, strategy_code, timeframe,
                        economic_score, reliability_score, execution_score, risk_score,
                        edge_score_v2, model_verdict, source_version
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id;
                """, (
                    row["candidate_id"], row["symbol"], row["strategy_code"], row["timeframe"],
                    economic, reliability, execution, risk, edge_v2, "ACTIVE", SOURCE_VERSION
                ))
                model_id = cur.fetchone()["id"]

                for code, (raw, normalized) in metrics.items():
                    w = weights.get(code, Decimal("0"))
                    cur.execute("""
                        INSERT INTO analytics.edge_score_metric_v2 (
                            model_id, metric_code, raw_value, normalized_value,
                            weight, contribution, source_version
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s);
                    """, (
                        model_id, code, raw, normalized, w, normalized * w, SOURCE_VERSION
                    ))

    print("VERDICT=EDGE_SCORE_MODEL_V2_PART1_READY")


if __name__ == "__main__":
    main()
