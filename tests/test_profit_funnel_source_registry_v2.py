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


def test_only_real_profit_fact_claims_explicit_scope() -> None:
    explicit=[item for item in profit_funnel_source_definitions_v2() if item.scope_explicit]
    assert len(explicit)==1
    assert explicit[0].stage is ProfitFunnelStageV2.PROFIT
    assert "DATA_SCOPE='REAL'" in explicit[0].sql.upper()


def test_research_stage_uses_the_actual_discovery_run() -> None:
    research=profit_funnel_source_definitions_v2()[0]
    assert research.stage is ProfitFunnelStageV2.RESEARCH
    assert research.source_identity == "analytics.edge_discovery_run_v1.latest_done"
    assert "OBSERVATIONS_SCANNED" in research.sql.upper()
