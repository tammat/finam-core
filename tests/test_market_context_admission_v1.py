from datetime import datetime, timedelta, timezone
from pathlib import Path

from finam_core.analytics.market_context_admission_v1 import (
    decide_market_context_admission_v1,
    independent_candidate_key_v1,
)


def test_context_modes_keep_incomplete_context_out_of_paper() -> None:
    now = datetime(2026, 7, 31, 4, 15, tzinfo=timezone.utc)
    full = decide_market_context_admission_v1(
        now=now,
        index_bar_ts=now - timedelta(minutes=1),
        rvi_bar_ts=now - timedelta(minutes=2),
    )
    index_only = decide_market_context_admission_v1(
        now=now,
        index_bar_ts=now - timedelta(minutes=1),
        rvi_bar_ts=now - timedelta(hours=2),
    )
    unavailable = decide_market_context_admission_v1(
        now=now,
        index_bar_ts=now - timedelta(hours=2),
        rvi_bar_ts=now - timedelta(minutes=2),
    )
    assert (full.mode, full.shadow_allowed, full.paper_allowed) == ("FULL", True, True)
    assert (index_only.mode, index_only.shadow_allowed, index_only.paper_allowed) == (
        "INDEX_ONLY", True, False
    )
    assert (unavailable.mode, unavailable.shadow_allowed, unavailable.paper_allowed) == (
        "UNAVAILABLE", False, False
    )


def test_candidate_embargo_is_stable_but_allows_material_move() -> None:
    event_ts = datetime(2026, 7, 31, 4, 5, tzinfo=timezone.utc)
    common = dict(
        strategy="MEAN_REVERSION_EQUITY",
        symbol="SBER@MISX",
        side="BUY",
        event_ts=event_ts,
        atr=1.0,
        regime="RANGE",
        futures=False,
    )
    first = independent_candidate_key_v1(price=100.01, **common)
    duplicate = independent_candidate_key_v1(price=100.20, **common)
    material_move = independent_candidate_key_v1(price=100.70, **common)
    assert duplicate == first
    assert material_move != first


def test_pipeline_persists_index_only_as_shadow_not_paper() -> None:
    source = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert "PIPE_PRE_SIGNAL_SHADOW_SAVED" in source
    assert '"paper_allowed": False' in source
    assert "repository.mark_rejected" in source
    assert "market_context.shadow_allowed" in source


def test_daily_funnel_starts_before_signals() -> None:
    source = Path(
        "src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py"
    ).read_text()
    assert "Кандидаты входа" in source
    assert "Блокировки до сигнала" in source
    assert "runtime_guard_pre_signal_block_audit_v1" in source
