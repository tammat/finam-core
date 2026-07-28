from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_risk_decision_schema_contains_every_field_written_by_gate():
    gate = (ROOT / "src/finam_core/risk/portfolio_risk_gate.py").read_text()
    migration = (ROOT / "sql/analytics/180_risk_control_hard_gate_v1.sql").read_text()

    required = {
        "entry_price",
        "stop_price",
        "contract_multiplier",
        "projected_cluster_share",
        "degradation_status",
    }
    for field in required:
        assert field in gate
        assert f"ADD COLUMN IF NOT EXISTS {field}" in migration


def test_paper_pipeline_passes_position_inputs_to_portfolio_gate():
    pipeline = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert "def _portfolio_risk_inputs_v1" in pipeline
    assert 'intent.get("entry_price")' in pipeline
    assert 'intent.get("stop_price")' in pipeline
    assert 'getattr(spec, "step_value"' in pipeline
    assert "**position_risk_inputs" in pipeline
