from pathlib import Path


def test_adaptive_scenarios_inherit_canonical_methodology_contracts() -> None:
    source = Path("src/scripts/build_edge_hypothesis_discovery_v1.py").read_text(
        encoding="utf-8"
    )
    assert "r.regime_policy AS canonical_regime_policy" in source
    assert "r.gate_policy AS canonical_gate_policy" in source
    assert '"target_symbols": [row["target_symbol"]]' in source
    assert '"gate_policy": row["canonical_gate_policy"]' in source


def test_unfinished_tasks_are_repaired_without_rewriting_history() -> None:
    migration = Path(
        "sql/analytics/173_adaptive_regime_contract_repair_v1.sql"
    ).read_text(encoding="utf-8")
    assert "task.status_code IN ('PENDING', 'RUNNING')" in migration
    assert "registry.regime_policy" in migration
    assert "registry.gate_policy" in migration
    assert "COMPLETE" not in migration
