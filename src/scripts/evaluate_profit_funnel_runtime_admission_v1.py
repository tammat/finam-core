from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import Json


POLICY_VERSION = "RUNTIME_ADMISSION_POLICY_V1"
EVALUATOR_VERSION = "PROFIT_FUNNEL_RUNTIME_ADMISSION_EVALUATOR_V1"
NAMESPACE = uuid.UUID("54ac13af-e57e-59e8-b70c-6b0cb734a31b")
MIN_OOS_TRADES = 30
MIN_FOLDS = 3
MIN_PAPER_TRADES = 30
MIN_PAPER_SESSIONS = 10
MAX_EVIDENCE_AGE = timedelta(days=7)


def _number(value: Any) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)))


def evaluate(evidence: dict[str, Any], *, now: datetime) -> tuple[str, list[str]]:
    failures: list[str] = []
    if evidence.get("paper_status") != "ACTIVE":
        failures.append("PAPER_NOT_ACTIVE")
    if evidence.get("candidate_status") != "OOS_PASS":
        failures.append("CANDIDATE_NOT_OOS_PASS")
    if not evidence.get("paper_allowed"):
        failures.append("PAPER_NOT_ALLOWED")
    if evidence.get("verdict_code") != "OOS_PASS" or not evidence.get("promotion_allowed"):
        failures.append("OOS_PROMOTION_NOT_ALLOWED")
    if int(evidence.get("oos_trades") or 0) < MIN_OOS_TRADES:
        failures.append("OOS_TRADES_INSUFFICIENT")
    if int(evidence.get("folds_total") or 0) < MIN_FOLDS or (
        int(evidence.get("folds_passed") or 0) != int(evidence.get("folds_total") or 0)
    ):
        failures.append("OOS_FOLDS_NOT_ALL_PASSED")
    if (_number(evidence.get("oos_profit_factor")) or 0) <= 1:
        failures.append("OOS_PROFIT_FACTOR_NOT_POSITIVE")
    if (_number(evidence.get("oos_expectancy")) or 0) <= 0:
        failures.append("OOS_EXPECTANCY_NOT_POSITIVE")
    if not evidence.get("evidence_ready"):
        failures.append("PAPER_EVIDENCE_NOT_READY")
    if int(evidence.get("closed_trades") or 0) < MIN_PAPER_TRADES:
        failures.append("PAPER_TRADES_INSUFFICIENT")
    if int(evidence.get("trading_sessions") or 0) < MIN_PAPER_SESSIONS:
        failures.append("PAPER_SESSIONS_INSUFFICIENT")
    if (_number(evidence.get("net_profit_factor")) or 0) <= 1:
        failures.append("PAPER_PROFIT_FACTOR_NOT_POSITIVE")
    if (_number(evidence.get("net_expectancy")) or 0) <= 0:
        failures.append("PAPER_EXPECTANCY_NOT_POSITIVE")
    refreshed_at = evidence.get("evidence_refreshed_at")
    if not isinstance(refreshed_at, datetime) or now - refreshed_at > MAX_EVIDENCE_AGE:
        failures.append("PAPER_EVIDENCE_STALE")
    return ("FAIL", failures) if failures else ("PASS", ["ALL_RUNTIME_ADMISSION_GATES_PASSED"])


def _json_evidence(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.isoformat() if isinstance(value, datetime)
        else _number(value) if isinstance(value, Decimal)
        else value
        for key, value in row.items()
        if key != "admission_id"
    }


def main() -> int:
    now = datetime.now(timezone.utc)
    passed = failed = 0
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    a.admission_id,p.paper_status,c.candidate_status,c.paper_allowed,
                    o.verdict_code,o.promotion_allowed,o.oos_trades,o.folds_total,
                    o.folds_passed,o.oos_profit_factor,o.oos_expectancy,
                    e.closed_trades,e.trading_sessions,e.net_profit_factor,
                    e.net_expectancy,e.evidence_ready,e.refreshed_at AS evidence_refreshed_at
                FROM analytics.profit_funnel_paper_runtime_admission_v2 a
                JOIN analytics.paper_runtime_candidate_v1 p ON p.id=a.paper_candidate_id
                JOIN analytics.edge_candidate_v1 c ON c.observation_uuid=a.observation_uuid
                LEFT JOIN analytics.edge_oos_result_v1 o ON o.observation_uuid=a.observation_uuid
                LEFT JOIN analytics.paper_evidence_readiness_v1 e ON e.timeframe=p.timeframe
                ORDER BY a.admission_id
            """)
            columns = [item.name for item in cursor.description]
            rows = [dict(zip(columns, values)) for values in cursor.fetchall()]
            for row in rows:
                admission_id = row["admission_id"]
                decision_code, reasons = evaluate(row, now=now)
                evidence = _json_evidence(row)
                fingerprint = json.dumps(
                    {"policy": POLICY_VERSION, "decision": decision_code,
                     "reasons": reasons, "evidence": evidence},
                    ensure_ascii=True, sort_keys=True, separators=(",", ":"),
                )
                decision_id = uuid.uuid5(NAMESPACE, f"{admission_id}:{fingerprint}")
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_runtime_admission_decision_v1 (
                        decision_id,admission_id,decision_code,policy_version,
                        reason_codes,evidence,evaluator_version,evaluated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (decision_id) DO NOTHING
                """, (
                    str(decision_id),str(admission_id),decision_code,POLICY_VERSION,
                    Json(reasons),Json(evidence),EVALUATOR_VERSION,now,
                ))
                is_pass = decision_code == "PASS"
                cursor.execute("""
                    UPDATE analytics.profit_funnel_paper_runtime_admission_v2
                    SET admission_status=%s,reason_code=%s,runtime_allowed=%s,
                        execution_enabled=false,live_allowed=false,
                        decision_id=%s,decision_code=%s,policy_version=%s,
                        decided_at=%s,updated_at=clock_timestamp()
                    WHERE admission_id=%s
                """, (
                    "ADMITTED" if is_pass else "PENDING",
                    "RUNTIME_ADMISSION_PASS" if is_pass else reasons[0],
                    is_pass,str(decision_id),decision_code,POLICY_VERSION,now,
                    str(admission_id),
                ))
                passed += int(is_pass)
                failed += int(not is_pass)
    print(f"runtime_admission_passed={passed}")
    print(f"runtime_admission_failed={failed}")
    print("execution_enabled=0")
    print("live_allowed=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
