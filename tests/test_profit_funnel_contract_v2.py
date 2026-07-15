from datetime import datetime, timezone
from decimal import Decimal

import pytest

from marketcore.core.profit_funnel_contract_v2 import (
    ProfitFunnelContractErrorV2,
    ProfitFunnelDataScopeV2,
    ProfitFunnelFreshnessV2,
    ProfitFunnelSnapshotV2,
    ProfitFunnelStageMetricV2,
    ProfitFunnelStageV2,
    validate_profit_funnel_snapshot_v2,
)


NOW = datetime(2026, 7, 15, 20, 0, tzinfo=timezone.utc)


def metric(stage, count, previous, *, scope=ProfitFunnelDataScopeV2.REAL, cohort="cohort-1", freshness=ProfitFunnelFreshnessV2.CURRENT, quality="VERIFIED"):
    return ProfitFunnelStageMetricV2(
        stage, cohort, scope, count, previous,
        None if previous is None else Decimal(count) / Decimal(previous or 1),
        None if previous is None else 60, freshness, {}, Decimal("0"), Decimal("0"), Decimal("0"),
        f"analytics.source_{stage.value.lower()}", None if freshness is ProfitFunnelFreshnessV2.UNAVAILABLE else NOW,
        NOW, quality,
    )


def snapshot(replacements=None):
    replacements = replacements or {}
    stages=[]
    previous=None
    for index, stage in enumerate(ProfitFunnelStageV2):
        item=metric(stage,10-index,previous)
        item=replacements.get(stage,item)
        stages.append(item);previous=item.count
    return ProfitFunnelSnapshotV2("cohort-1",ProfitFunnelDataScopeV2.REAL,NOW,tuple(stages))


def test_complete_real_funnel_is_valid() -> None:
    assert validate_profit_funnel_snapshot_v2(snapshot()).data_scope is ProfitFunnelDataScopeV2.REAL


def test_all_ten_stages_are_required_in_order() -> None:
    value=snapshot()
    with pytest.raises(ProfitFunnelContractErrorV2,match="STAGE_SEQUENCE"):
        validate_profit_funnel_snapshot_v2(ProfitFunnelSnapshotV2(value.cohort_id,value.data_scope,value.generated_at,value.stages[:-1]))


def test_test_data_cannot_enter_real_snapshot() -> None:
    bad=metric(ProfitFunnelStageV2.PAPER,4,5,scope=ProfitFunnelDataScopeV2.TEST)
    with pytest.raises(ProfitFunnelContractErrorV2,match="SCOPE_MISMATCH"):
        validate_profit_funnel_snapshot_v2(snapshot({ProfitFunnelStageV2.PAPER:bad}))


def test_stale_data_cannot_be_verified() -> None:
    bad=metric(ProfitFunnelStageV2.FORWARD,5,6,freshness=ProfitFunnelFreshnessV2.STALE)
    with pytest.raises(ProfitFunnelContractErrorV2,match="STALE_VERIFIED_FORBIDDEN"):
        validate_profit_funnel_snapshot_v2(snapshot({ProfitFunnelStageV2.FORWARD:bad}))


def test_unavailable_freshness_has_no_invented_source_time() -> None:
    bad=metric(ProfitFunnelStageV2.LIVE,2,3,freshness=ProfitFunnelFreshnessV2.UNAVAILABLE,quality="UNVERIFIED")
    value=snapshot({ProfitFunnelStageV2.LIVE:bad})
    assert validate_profit_funnel_snapshot_v2(value).stages[8].source_as_of is None


def test_previous_count_must_reconcile() -> None:
    bad=metric(ProfitFunnelStageV2.SHADOW,4,99)
    with pytest.raises(ProfitFunnelContractErrorV2,match="PREVIOUS_COUNT_MISMATCH"):
        validate_profit_funnel_snapshot_v2(snapshot({ProfitFunnelStageV2.SHADOW:bad}))
