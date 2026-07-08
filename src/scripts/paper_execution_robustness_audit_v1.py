from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1"


def dec(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def load_params(cur) -> dict[str, Decimal]:
    cur.execute("""
        SELECT parameter_code, parameter_value
        FROM knowledge.platform_parameter_v1
        WHERE parameter_group='PAPER_ROBUSTNESS'
          AND enabled
    """)
    return {str(r["parameter_code"]): dec(r["parameter_value"]) for r in cur.fetchall()}


def score(count_value: int, required_value: Decimal, score_max: Decimal) -> Decimal:
    if required_value <= 0:
        return score_max
    raw = Decimal(count_value) / required_value * score_max
    return min(raw, score_max).quantize(Decimal("0.0001"))


def status_from_sample(trades: int, validated_min: Decimal, production_min: Decimal) -> str:
    if Decimal(trades) >= production_min:
        return "PRODUCTION"
    if Decimal(trades) >= validated_min:
        return "VALIDATED"
    return "RESEARCH"


def overfit_risk_from_status(sample_status: str) -> str:
    if sample_status == "PRODUCTION":
        return "LOW"
    if sample_status == "VALIDATED":
        return "MEDIUM"
    return "HIGH"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            params = load_params(cur)

            required = {
                "ROBUSTNESS_VALIDATED_MIN_TRADES",
                "ROBUSTNESS_PRODUCTION_MIN_TRADES",
                "ROBUSTNESS_MIN_TIME_BUCKETS",
                "ROBUSTNESS_MIN_INSTRUMENTS",
                "ROBUSTNESS_MIN_REGIMES",
                "ROBUSTNESS_MIN_SOURCES",
                "ROBUSTNESS_SCORE_MAX",
            }
            missing = required - set(params)
            if missing:
                raise RuntimeError(f"missing_robustness_parameters:{sorted(missing)}")

            score_max = params["ROBUSTNESS_SCORE_MAX"]

            cur.execute("""
                SELECT analytics_snapshot_id
                FROM analytics.analytics_snapshot_v1
                WHERE snapshot_type='PAPER_EXECUTION_ANALYTICS'
                  AND source_version='PAPER_EXECUTION_ANALYTICS_ENGINE_V1'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            paper_snapshot = cur.fetchone()
            if not paper_snapshot:
                raise RuntimeError("missing_paper_analytics_snapshot")

            paper_snapshot_id = int(paper_snapshot["analytics_snapshot_id"])

            cur.execute("""
                SELECT
                    count(*) AS trades,
                    count(DISTINCT symbol) AS instruments,
                    count(DISTINCT timeframe) AS timeframes,
                    count(DISTINCT date_trunc('day', created_at)) AS time_buckets
                FROM knowledge.paper_execution_result_v1
                WHERE source_version='PAPER_EXECUTION_SIMULATOR_V1'
            """)
            base = cur.fetchone()

            cur.execute("""
                SELECT count(DISTINCT regime_code) AS regimes
                FROM analytics.paper_execution_regime_scorecard_v1
                WHERE analytics_snapshot_id=%s
            """, (paper_snapshot_id,))
            regimes = int(cur.fetchone()["regimes"] or 0)

            cur.execute("""
                SELECT count(*) AS sources
                FROM analytics.paper_execution_source_scorecard_v1
                WHERE analytics_snapshot_id=%s
            """, (paper_snapshot_id,))
            sources = int(cur.fetchone()["sources"] or 0)

            trades = int(base["trades"] or 0)
            instruments = int(base["instruments"] or 0)
            time_buckets = int(base["time_buckets"] or 0)

            sample_score = score(trades, params["ROBUSTNESS_PRODUCTION_MIN_TRADES"], score_max)
            time_score = score(time_buckets, params["ROBUSTNESS_MIN_TIME_BUCKETS"], score_max)
            instrument_score = score(instruments, params["ROBUSTNESS_MIN_INSTRUMENTS"], score_max)
            regime_score = score(regimes, params["ROBUSTNESS_MIN_REGIMES"], score_max)
            source_score = score(sources, params["ROBUSTNESS_MIN_SOURCES"], score_max)

            robustness_score = (
                sample_score + time_score + instrument_score + regime_score + source_score
            ) / Decimal("5")

            learning_readiness = robustness_score

            sample_status = status_from_sample(
                trades,
                params["ROBUSTNESS_VALIDATED_MIN_TRADES"],
                params["ROBUSTNESS_PRODUCTION_MIN_TRADES"],
            )
            overfit_risk = overfit_risk_from_status(sample_status)

            cur.execute("""
                INSERT INTO analytics.analytics_snapshot_v1
                (snapshot_type, source_version, evidence_json)
                VALUES (%s,%s,%s::jsonb)
                RETURNING analytics_snapshot_id
            """, (
                "PAPER_EXECUTION_ROBUSTNESS",
                SOURCE_VERSION,
                json.dumps(
                    {
                        "paper_analytics_snapshot_id": paper_snapshot_id,
                        "mode": "audit_only_no_auto_decision",
                        "parameters_source": "knowledge.platform_parameter_v1",
                    },
                    ensure_ascii=False,
                ),
            ))
            robustness_snapshot_id = int(cur.fetchone()["analytics_snapshot_id"])

            cur.execute("""
                INSERT INTO analytics.paper_execution_robustness_audit_v1
                (
                    analytics_snapshot_id,
                    paper_analytics_snapshot_id,
                    sample_trades,
                    time_bucket_count,
                    instrument_count,
                    regime_count,
                    source_count,
                    sample_score,
                    time_stability_score,
                    instrument_stability_score,
                    regime_stability_score,
                    source_stability_score,
                    robustness_score,
                    learning_readiness_index,
                    sample_status,
                    overfit_risk,
                    production_allowed,
                    auto_decision,
                    evidence_json,
                    source_version
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,%s::jsonb,%s)
            """, (
                robustness_snapshot_id,
                paper_snapshot_id,
                trades,
                time_buckets,
                instruments,
                regimes,
                sources,
                sample_score,
                time_score,
                instrument_score,
                regime_score,
                source_score,
                robustness_score.quantize(Decimal("0.0001")),
                learning_readiness.quantize(Decimal("0.0001")),
                sample_status,
                overfit_risk,
                json.dumps(
                    {
                        "validated_min_trades": str(params["ROBUSTNESS_VALIDATED_MIN_TRADES"]),
                        "production_min_trades": str(params["ROBUSTNESS_PRODUCTION_MIN_TRADES"]),
                        "min_time_buckets": str(params["ROBUSTNESS_MIN_TIME_BUCKETS"]),
                        "min_instruments": str(params["ROBUSTNESS_MIN_INSTRUMENTS"]),
                        "min_regimes": str(params["ROBUSTNESS_MIN_REGIMES"]),
                        "min_sources": str(params["ROBUSTNESS_MIN_SOURCES"]),
                    },
                    ensure_ascii=False,
                ),
                SOURCE_VERSION,
            ))

    print("=== PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1 ===")
    print(f"analytics_snapshot_id={robustness_snapshot_id}")
    print(f"paper_analytics_snapshot_id={paper_snapshot_id}")
    print(f"sample_trades={trades}")
    print(f"time_bucket_count={time_buckets}")
    print(f"instrument_count={instruments}")
    print(f"regime_count={regimes}")
    print(f"source_count={sources}")
    print(f"robustness_score={robustness_score.quantize(Decimal('0.0001'))}")
    print(f"learning_readiness_index={learning_readiness.quantize(Decimal('0.0001'))}")
    print(f"sample_status={sample_status}")
    print(f"overfit_risk={overfit_risk}")
    print("production_allowed=0")
    print("auto_decision=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1_READY")


if __name__ == "__main__":
    main()
