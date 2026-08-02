from pathlib import Path


def test_market_workers_start_before_equity_morning_session() -> None:
    migration = Path("sql/analytics/267_market_session_start_alignment_v1.sql").read_text()
    assert "time '06:40'" in migration
    for job in (
        "FORWARD_PASS_SHADOW_OBSERVER",
        "SHADOW_PIPELINE_MONITOR",
        "SHADOW_PASS_EVALUATOR",
    ):
        assert job in migration


def test_preflight_runs_with_warmup_margin() -> None:
    timer = Path("deploy/systemd/finam-monday-preflight-v2.timer").read_text()
    for moment in ("06:20:00", "06:35:00", "06:45:00"):
        assert moment in timer
    assert "06:56:00" not in timer
