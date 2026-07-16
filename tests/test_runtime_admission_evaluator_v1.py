from datetime import datetime, timedelta, timezone

from scripts.evaluate_profit_funnel_runtime_admission_v1 import evaluate
from pathlib import Path


def _passing_evidence() -> dict:
    return {
        "paper_status": "ACTIVE",
        "candidate_status": "OOS_PASS",
        "paper_allowed": True,
        "verdict_code": "OOS_PASS",
        "promotion_allowed": True,
        "oos_trades": 100,
        "folds_total": 3,
        "folds_passed": 3,
        "oos_profit_factor": 1.2,
        "oos_expectancy": 0.1,
        "closed_trades": 40,
        "trading_sessions": 12,
        "net_profit_factor": 1.1,
        "net_expectancy": 0.01,
        "evidence_ready": True,
        "evidence_refreshed_at": datetime.now(timezone.utc) - timedelta(hours=1),
    }


def test_pass_requires_every_gate() -> None:
    decision, reasons = evaluate(_passing_evidence(), now=datetime.now(timezone.utc))
    assert decision == "PASS"
    assert reasons == ["ALL_RUNTIME_ADMISSION_GATES_PASSED"]


def test_negative_paper_expectancy_fails() -> None:
    evidence = _passing_evidence()
    evidence["net_expectancy"] = -0.01
    decision, reasons = evaluate(evidence, now=datetime.now(timezone.utc))
    assert decision == "FAIL"
    assert "PAPER_EXPECTANCY_NOT_POSITIVE" in reasons


def test_stale_evidence_fails() -> None:
    evidence = _passing_evidence()
    evidence["evidence_refreshed_at"] = datetime.now(timezone.utc) - timedelta(days=8)
    decision, reasons = evaluate(evidence, now=datetime.now(timezone.utc))
    assert decision == "FAIL"
    assert "PAPER_EVIDENCE_STALE" in reasons


def test_migration_requires_pass_and_append_only_audit() -> None:
    migration = Path("sql/analytics/064_runtime_admission_pass_gate_v1.sql").read_text()
    assert "decision_code = 'PASS'" in migration
    assert "admission_status = 'ADMITTED'" in migration
    assert "NOT execution_enabled" in migration
    assert "NOT live_allowed" in migration
    assert "RUNTIME_ADMISSION_DECISION_AUDIT_IS_APPEND_ONLY" in migration
