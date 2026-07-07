from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "EDGE_FACTORY_BOTTLENECK_ANALYZER_V1"
OUT_JSON = Path("reports/edge_factory_bottleneck_latest.json")
OUT_TXT = Path("reports/edge_factory_bottleneck_latest.txt")


def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def scalar(cur, sql: str) -> Decimal:
    cur.execute(sql)
    row = cur.fetchone()
    if not row:
        return Decimal("0")
    return Decimal(str(list(row.values())[0] or 0))


def conversion_pct(source: Decimal, target: Decimal) -> Decimal:
    if source <= 0:
        return Decimal("0")
    return (target / source * Decimal("100")).quantize(Decimal("0.000001"))


def severity(conv: Decimal) -> str:
    if conv < Decimal("5"):
        return "CRITICAL"
    if conv < Decimal("20"):
        return "HIGH"
    if conv < Decimal("50"):
        return "MEDIUM"
    return "LOW"


def classify(stage: str) -> tuple[str, str, Decimal]:
    if stage == "RESEARCH_TO_OBSERVATION":
        return "LOW_OBSERVATION_YIELD", "COLLECT_MORE_DATA", Decimal("10")
    if stage == "OBSERVATION_TO_CANDIDATE":
        return "LOW_CANDIDATE_YIELD", "EXPAND_PARAMETERS", Decimal("18")
    if stage == "CANDIDATE_TO_PAPER":
        return "LOW_PAPER_YIELD", "PAPER_REPRICE", Decimal("9")
    return "NO_DATA", "NO_ACTION", Decimal("0")


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            research = scalar(cur, "SELECT count(*) FROM analytics.parameter_search_job_v1")
            observations = scalar(cur, "SELECT count(*) FROM analytics.edge_observation_v1")
            candidates = scalar(cur, "SELECT count(*) FROM analytics.edge_candidate_v1")
            paper = scalar(cur, "SELECT count(*) FROM analytics.paper_runtime_candidate_v1 WHERE paper_status='ACTIVE'")
            unsafe = scalar(cur, "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE micro_live_allowed=true OR live_allowed=true")

            transitions = [
                ("RESEARCH_TO_OBSERVATION", research, observations),
                ("OBSERVATION_TO_CANDIDATE", observations, candidates),
                ("CANDIDATE_TO_PAPER", candidates, paper),
            ]

            ranked = [
                {
                    "pipeline_stage": stage,
                    "source_count": src,
                    "target_count": dst,
                    "conversion_pct": conversion_pct(src, dst),
                }
                for stage, src, dst in transitions
            ]

            bottleneck = sorted(ranked, key=lambda x: x["conversion_pct"])[0]
            root_cause, recommendation, expected_gain = classify(bottleneck["pipeline_stage"])
            sev = severity(bottleneck["conversion_pct"])
            status = "ACTIVE" if unsafe == 0 else "UNSAFE_BLOCKED"

            cur.execute(
                """
                INSERT INTO analytics.edge_factory_bottleneck_v1 (
                    pipeline_stage,
                    source_count,
                    target_count,
                    conversion_pct,
                    severity,
                    root_cause_code,
                    recommendation_code,
                    expected_gain_pct,
                    source_version
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    bottleneck["pipeline_stage"],
                    int(bottleneck["source_count"]),
                    int(bottleneck["target_count"]),
                    bottleneck["conversion_pct"],
                    sev,
                    root_cause,
                    recommendation,
                    expected_gain,
                    SOURCE_VERSION,
                ),
            )

    payload = {
        "source_version": SOURCE_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline": ranked,
        "bottleneck": {
            **bottleneck,
            "severity": sev,
            "root_cause_code": root_cause,
            "recommendation_code": recommendation,
            "expected_gain_pct": expected_gain,
            "status": status,
        },
        "unsafe_rows": unsafe,
        "verdict": "EDGE_FACTORY_BOTTLENECK_ANALYZER_READY" if unsafe == 0 else "UNSAFE_ROWS_FOUND",
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    lines = [
        "=== EDGE_FACTORY_BOTTLENECK_ANALYZER_V1 ===",
        f"pipeline_stage={bottleneck['pipeline_stage']}",
        f"source_count={bottleneck['source_count']}",
        f"target_count={bottleneck['target_count']}",
        f"conversion_pct={bottleneck['conversion_pct']}",
        f"severity={sev}",
        f"root_cause_code={root_cause}",
        f"recommendation_code={recommendation}",
        f"expected_gain_pct={expected_gain}",
        f"unsafe_rows={unsafe}",
        f"VERDICT={payload['verdict']}",
    ]
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
