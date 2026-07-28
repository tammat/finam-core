from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_db_admission_rejects_incomplete_rolled_and_m1_variants_before_oos() -> None:
    migration = (ROOT / "sql/analytics/178_oos_admission_hygiene_v1.sql").read_text()
    for code in (
        "OOS_SPECIFICATION_INCOMPLETE",
        "OOS_CONTRACT_ROLLED",
        "OOS_M1_MICROSTRUCTURE_REQUIRED",
    ):
        assert code in migration
    assert "oos_variant_admission_reason_v1" in migration
    assert "PRUNED_STALE" in migration


def test_legacy_oos_and_temporal_generator_use_the_shared_db_admission_gate() -> None:
    legacy = (ROOT / "src/scripts/build_momentum_edge_oos_rank_v1.py").read_text()
    temporal = (ROOT / "src/scripts/generate_temporal_oos_branches_v1.py").read_text()
    assert "oos_variant_admission_reason_v1" in legacy
    assert "oos_variant_admission_reason_v1" in temporal
    assert "market_microstructure_snapshot_v1" in temporal
