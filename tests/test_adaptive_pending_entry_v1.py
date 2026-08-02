import pytest

from finam_core.analytics.entry_exit_optimizer import Bar, candidate_policy_code
from finam_core.execution.adaptive_pending_entry_v1 import evaluate_pending_entry_v1


def test_confirmation_uses_completed_close():
    result = evaluate_pending_entry_v1(
        mode="CONFIRM_1",side="LONG",signal_price=100,atr=1,
        bars=[Bar(high=101.2,low=99.8,close=100.8)])
    assert result.status == "READY" and result.entry_price == 100.8


def test_retest_waits_and_then_cancels_after_three_bars():
    waiting = evaluate_pending_entry_v1(
        mode="RETEST_3",side="LONG",signal_price=100,atr=1,
        bars=[Bar(high=100.5,low=100.3,close=100.4)])
    assert waiting.status == "PENDING"
    cancelled = evaluate_pending_entry_v1(
        mode="RETEST_3",side="LONG",signal_price=100,atr=1,
        bars=[Bar(100.5,100.3,100.4),Bar(100.5,100.3,100.4),Bar(100.5,100.3,100.4)])
    assert cancelled.status == "CANCELLED"


def test_retest_ambiguous_runaway_fails_closed():
    result = evaluate_pending_entry_v1(
        mode="RETEST_3",side="LONG",signal_price=100,atr=1,
        bars=[Bar(high=100.8,low=100.1,close=100.2)])
    assert result.status == "CANCELLED"


def test_paper_pipeline_persists_and_consumes_pending_entry_fail_closed():
    source = open("src/finam_core/pipelines/paper_pipeline.py", encoding="utf-8").read()
    assert "entry_exit_pending_entry_v1" in source
    assert "adaptive_entry_decision(" in source
    assert "PIPE_ENTRY_EXIT_PROFILE_FAIL_CLOSED" in source
    assert "status='CONSUMED'" in source


def test_pending_worker_reads_only_completed_bars():
    source = open(
        "src/scripts/run_adaptive_pending_entry_worker_v1.py", encoding="utf-8"
    ).read()
    assert "ts>%s AND ts<=%s" in source
    assert "now-delta" in source


def test_frozen_expert_candidate_resolves_exact_policy():
    assert candidate_policy_code("EXPERT_BR_RETEST_VOLUME") == "EXPERT_BR"
    assert candidate_policy_code("EXPERT_GOLD_CONFIRM_MTF") == "EXPERT_GOLD"
    assert candidate_policy_code("EXPERT_FX_RETEST_COST") == "EXPERT_FX"
    assert candidate_policy_code("EXPERT_EQUITY_RANGE_RETEST") == "EXPERT_EQUITY_MR"


def test_unknown_expert_candidate_fails_closed():
    with pytest.raises(ValueError):
        candidate_policy_code("EXPERT_UNKNOWN")


def test_pipeline_uses_source_event_time_and_no_feature_defaults():
    source = open("src/finam_core/pipelines/paper_pipeline.py", encoding="utf-8").read()
    assert "APPROVED_PROFILE_SOURCE_EVENT_TS_MISSING" in source
    assert "APPROVED_PROFILE_M15_ALIGNMENT_MISSING" in source
    assert 'policy_code=policy_code' in source
    assert "clock_timestamp(),%s,%s,%s,%s::jsonb" not in source
