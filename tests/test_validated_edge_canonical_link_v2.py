from pathlib import Path
from datetime import datetime, timezone

from scripts.build_profit_funnel_validated_edge_v2 import specification_reason


def test_validated_edge_uses_exact_candidate_identity() -> None:
    source = Path("src/scripts/build_profit_funnel_transition_lineage_v2.py").read_text()
    assert "v.candidate_uuid=c.candidate_uuid" in source
    assert 'reason_code="CANDIDATE_UUID_FULL_MATCH"' in source


def test_validated_edge_cannot_enable_trading() -> None:
    migration = Path("sql/analytics/056_profit_funnel_validated_edge_v2.sql").read_text()
    assert "CHECK (NOT paper_allowed AND NOT runtime_allowed AND NOT live_allowed)" in migration


def test_validated_edge_rejects_incomplete_specs_and_expired_contracts() -> None:
    now = datetime(2026, 7, 17, tzinfo=timezone.utc)
    assert specification_reason({}, "SBER@MISX", now) == "VALIDATED_EDGE_SPECIFICATION_INCOMPLETE"
    no_cost = {"lookback": 40, "hold": 5, "threshold": 1.0, "commission": 0, "slippage": 0}
    assert specification_reason(no_cost, "SBER@MISX", now) == "VALIDATED_EDGE_COST_MODEL_MISSING"
    complete = {"lookback": 40, "hold": 5, "threshold": 1.0, "transaction_cost_bps": 8.0}
    assert specification_reason(complete, "BRM6@RTSX", now) == "VALIDATED_EDGE_CONTRACT_EXPIRED"
    assert specification_reason(complete, "BRQ6@RTSX", now) is None


def test_funnel_only_uses_active_validated_edges() -> None:
    registry = Path("src/marketcore/services/profit_funnel_source_registry_v2.py").read_text()
    lineage = Path("src/scripts/build_profit_funnel_transition_lineage_v2.py").read_text()
    migration = Path("sql/analytics/068_validated_edge_revocation_v1.sql").read_text()
    assert "WHERE validation_status='PASS'" in registry
    assert "v.validation_status='PASS'" in lineage
    assert "validation_status IN ('PASS','REVOKED')" in migration
