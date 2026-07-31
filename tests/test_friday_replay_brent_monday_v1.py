from pathlib import Path


def test_replay_report_is_read_only_and_monday_gate_is_fail_closed() -> None:
    source = Path(
        "src/scripts/analytics/build_friday_replay_brent_monday_readiness_v1.py"
    ).read_text()
    assert "entry_exit_signal_shadow_pair_v2" in source
    assert "diagnostic_only" in source
    assert "paper_profile_changed" in source
    assert "WAIT_2_COMPLETED_MX_M15_AND_FRESH_MX_RVI" in source
    assert "UPDATE analytics.entry_exit_runtime_profile" not in source
    assert "INSERT INTO analytics.entry_exit_runtime_profile" not in source


def test_pipeline_checks_monday_gate_before_execution() -> None:
    source = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert "PIPE_MONDAY_ENTRY_GATE_BLOCK" in source
    assert "paper_profile_changed=0" in source
    assert "self._reject_persisted_signal_v1(intent, monday_reason.lower())" in source
