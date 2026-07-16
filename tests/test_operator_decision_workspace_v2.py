from pathlib import Path
import re


def test_unverified_decisions_cannot_be_green_or_autonomous() -> None:
    migration = Path("sql/analytics/060_operator_decision_workspace_v2.sql").read_text()
    assert "CHECK (policy_verdict IN ('REVIEW_REQUIRED','BLOCKED'))" in migration
    assert "CHECK (quality_code='UNVERIFIED')" in migration
    assert "'ALLOWED'" not in migration


def test_decision_contains_required_evidence_and_rollback_fields() -> None:
    migration = Path("sql/analytics/060_operator_decision_workspace_v2.sql").read_text()
    for field in ("evidence JSONB", "source_as_of", "expected_profit_impact", "risk_impact_code", "confidence", "sample_sufficiency_code", "expires_at", "rollback_plan_code", "actual_result", "feedback_status"):
        assert field in migration


def test_operator_domain_codes_have_russian_catalog_entries() -> None:
    builder = Path("src/scripts/build_operator_decision_workspace_v2.py").read_text()
    migration = Path("sql/analytics/060_operator_decision_workspace_v2.sql").read_text()
    catalog = Path("sql/presentation/operator_decision_workspace_i18n_v2.sql").read_text()
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/home_v2_domain_renderer.py"
    ).read_text()

    emitted_codes = set(re.findall(r"'[A-Z][A-Z0-9_]{2,}'", builder + migration))
    required_codes = {
        code.strip("'")
        for code in emitted_codes
        if code.strip("'") in {
            "REVIEW_SHADOW_LOSS", "REVIEW_FORWARD_ADMISSION", "RESTORE_RUNTIME_EVIDENCE",
            "KEEP_LIVE_BLOCKED", "OBSERVE_REAL_EXECUTION_BOUNDARY",
            "NO_SHADOW_CANDIDATE_ELIGIBLE", "HANDOFF_PENDING_FORWARD_ADMISSION",
            "RUNTIME_ADMISSION_PENDING", "NO_RUNTIME_CANDIDATE_ADMITTED", "NO_REAL_EXECUTION",
            "REDUCE_LOSS_EXPOSURE", "NO_RISK_EXPANSION", "PREVENT_UNVERIFIED_LIVE",
            "PREVENT_UNAUTHORIZED_EXECUTION", "SUFFICIENT", "INSUFFICIENT", "NOT_APPLICABLE",
            "REVIEW_REQUIRED", "BLOCKED", "OPERATOR_APPROVAL", "OBSERVE_ONLY",
            "KEEP_PAPER_ADMISSION_BLOCKED", "CANCEL_FORWARD_HANDOFF", "CANCEL_RUNTIME_HANDOFF",
            "KEEP_LIVE_DISABLED", "PENDING", "MEASURED", "NOT_SELECTED", "ACKNOWLEDGED",
            "UNVERIFIED", "NO_DATA",
        }
    }
    catalog_keys = set(re.findall(r"home\.operator\.domain\.([a-z0-9_]+)", catalog))

    assert required_codes
    assert {code.lower() for code in required_codes} <= catalog_keys
    assert "_operator_domain_message_key" in renderer
    assert 'format_code == "DOMAIN_CODE"' in renderer
