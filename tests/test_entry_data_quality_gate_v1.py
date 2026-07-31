from datetime import datetime, timedelta, timezone

from finam_core.execution.entry_data_quality_gate_v1 import evaluate_entry_data_quality_v1


NOW = datetime(2026, 7, 29, 6, 0, tzinfo=timezone.utc)


def bars(step=60):
    return [NOW - timedelta(seconds=step * value) for value in (4, 3, 2)]


def test_passes_completed_continuous_bars_and_fresh_cost() -> None:
    decision = evaluate_entry_data_quality_v1(
        timeframe="M1", completed_bar_times=bars(), session_open=True,
        is_futures=True, cost_verified_at=NOW - timedelta(hours=1), now=NOW,
    )
    assert decision.allowed and decision.reason_code == "ENTRY_DATA_QUALITY_PASS"


def test_fails_closed_for_session_stale_gap_and_cost() -> None:
    common = dict(timeframe="M1", completed_bar_times=bars(), is_futures=False,
                  cost_verified_at=None, now=NOW)
    assert evaluate_entry_data_quality_v1(session_open=False, **common).reason_code == "MARKET_SESSION_CLOSED"
    assert evaluate_entry_data_quality_v1(
        session_open=True, **{**common, "completed_bar_times": [NOW-timedelta(minutes=x) for x in (12,11,10)]}
    ).reason_code == "COMPLETED_BAR_STALE"
    assert evaluate_entry_data_quality_v1(
        session_open=True, **{**common, "completed_bar_times": [NOW-timedelta(minutes=x) for x in (5,3,2)]}
    ).reason_code == "COMPLETED_BAR_SEQUENCE_GAP"
    assert evaluate_entry_data_quality_v1(
        timeframe="M1", completed_bar_times=bars(), session_open=True,
        is_futures=True, cost_verified_at=NOW-timedelta(days=3), now=NOW,
    ).reason_code == "CONTRACT_COST_SPEC_STALE"


def test_blocks_new_entry_near_session_close() -> None:
    decision = evaluate_entry_data_quality_v1(
        timeframe="M1", completed_bar_times=bars(), session_open=True,
        is_futures=False, cost_verified_at=None, now=NOW,
        session_minutes_remaining=20, entry_cutoff_minutes=30,
    )
    assert not decision.allowed
    assert decision.reason_code == "SESSION_CLOSE_ENTRY_CUTOFF"


def test_allows_entry_before_session_cutoff() -> None:
    decision = evaluate_entry_data_quality_v1(
        timeframe="M1", completed_bar_times=bars(), session_open=True,
        is_futures=False, cost_verified_at=None, now=NOW,
        session_minutes_remaining=31, entry_cutoff_minutes=30,
    )
    assert decision.allowed


def test_pipeline_applies_gate_only_to_entries_and_fails_closed() -> None:
    source = open("src/finam_core/pipelines/paper_pipeline.py", encoding="utf-8").read()
    assert "_entry_data_quality_gate_v1" in source
    assert "entry_data_quality:" in source
    assert "intent_type\") == \"EXIT\"" in source
    assert "ENTRY_DATA_QUALITY_GATE_ERROR" in source
