from pathlib import Path


def test_only_admitted_runtime_can_reach_live_boundary() -> None:
    source = Path("src/scripts/build_profit_funnel_runtime_live_admission_v2.py").read_text()
    assert "admission_status='ADMITTED' AND runtime_allowed" in source
    assert "INSERT INTO public.orders" not in source


def test_live_boundary_cannot_enable_execution() -> None:
    migration = Path("sql/analytics/059_profit_funnel_runtime_live_admission_v2.sql").read_text()
    assert "CHECK (NOT broker_order_allowed AND NOT execution_enabled AND NOT live_allowed)" in migration


def test_live_boundary_requires_proven_upstream_lineage() -> None:
    source = Path("src/scripts/build_profit_funnel_runtime_live_admission_v2.py").read_text()
    assert "count(*)=4" in source
    assert "'OOS_TO_FORWARD','FORWARD_TO_SHADOW'" in source
    assert "'SHADOW_TO_PAPER','PAPER_TO_RUNTIME'" in source
    assert "UPSTREAM_LINEAGE_NOT_PROVEN" in source
    assert "admission_status='CANCELLED'" in source
