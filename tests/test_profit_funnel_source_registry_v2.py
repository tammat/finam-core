from marketcore.core.profit_funnel_contract_v2 import ProfitFunnelStageV2
from marketcore.services.profit_funnel_source_registry_v2 import profit_funnel_source_definitions_v2


def test_every_stage_has_one_fixed_read_only_source() -> None:
    definitions=profit_funnel_source_definitions_v2()
    assert tuple(item.stage for item in definitions)==tuple(ProfitFunnelStageV2)
    assert len({item.source_identity for item in definitions})==10
    for item in definitions:
        sql=" ".join(item.sql.upper().split())
        assert sql.startswith("SELECT ")
        for forbidden in ("INSERT ","UPDATE ","DELETE ","ALTER ","DROP ","TRUNCATE "):
            assert forbidden not in sql


def test_only_real_execution_and_profit_claim_explicit_scope() -> None:
    explicit=[item for item in profit_funnel_source_definitions_v2() if item.scope_explicit]
    assert {item.stage for item in explicit} == {ProfitFunnelStageV2.LIVE, ProfitFunnelStageV2.PROFIT}
    live = next(item for item in explicit if item.stage is ProfitFunnelStageV2.LIVE)
    profit = next(item for item in explicit if item.stage is ProfitFunnelStageV2.PROFIT)
    assert "EXCHANGE_ORDER_ID IS NOT NULL" in live.sql.upper()
    assert "DATA_SCOPE='REAL'" in profit.sql.upper()


def test_research_stage_uses_the_actual_discovery_run() -> None:
    research=profit_funnel_source_definitions_v2()[0]
    assert research.stage is ProfitFunnelStageV2.RESEARCH
    assert research.source_identity == "analytics.edge_discovery_run_v1.latest_done"
    assert "OBSERVATIONS_SCANNED" in research.sql.upper()


def test_runtime_stage_uses_canonical_admission_records() -> None:
    runtime = next(
        item for item in profit_funnel_source_definitions_v2()
        if item.stage is ProfitFunnelStageV2.RUNTIME
    )
    assert runtime.source_identity == "analytics.profit_funnel_paper_runtime_admission_v2.admitted"
    assert "ADMISSION_STATUS='ADMITTED'" in runtime.sql.upper()
    assert "RUNTIME_ALLOWED" in runtime.sql.upper()


def test_oos_stage_counts_only_promotable_passes() -> None:
    oos = next(
        item for item in profit_funnel_source_definitions_v2()
        if item.stage is ProfitFunnelStageV2.OOS
    )
    assert "O.VERDICT_CODE='OOS_PASS'" in oos.sql.upper()
    assert "O.PROMOTION_ALLOWED=TRUE" in oos.sql.upper()


def test_forward_and_shadow_are_scoped_to_the_active_clean_cohort() -> None:
    definitions = profit_funnel_source_definitions_v2()
    for stage in (ProfitFunnelStageV2.FORWARD, ProfitFunnelStageV2.SHADOW):
        source = next(item for item in definitions if item.stage is stage)
        assert "FORWARD_EDGE_BASELINE_COHORT_ID_V1()" in source.sql.upper()
