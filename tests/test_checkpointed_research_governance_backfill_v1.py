from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_research_is_checkpointed_only_after_success() -> None:
    text = (ROOT / "src/scripts/research_pipeline_orchestrator.py").read_text()
    assert "checkpoint.is_current" in text
    assert "reason=NO_NEW_CLOSED_TRADES" in text
    assert "checkpoint.advance" in text
    assert text.index("checkpoint.advance") > text.index("rc = run_symbol")


def test_context_backfill_is_exact_past_only_and_quarantines_unknowns() -> None:
    for name in ("trade_risk_context_repository.py", "trade_exit_policy_repository.py"):
        text = (ROOT / "src/finam_core/analytics" / name).read_text()
        assert "g.strategy = s.strategy" in text
        assert "g.timeframe = s.timeframe" in text
        assert "g.created_at <= s.ctx_ts" in text
        assert "trade_context_quarantine_v1" in text
        assert "ABS(EXTRACT" not in text


def test_attribution_repair_uses_only_full_context() -> None:
    text = (ROOT / "src/scripts/backfill_trade_governance_context_v1.py").read_text()
    assert "r.context_quality='FULL'" in text
    assert "e.context_quality='FULL'" in text


def test_snapshot_quality_is_per_trade_and_strict() -> None:
    text = (ROOT / "src/scripts/build_trade_context_snapshots.py").read_text()
    assert "r.closed_trade_id=t.closed_trade_id" in text
    assert "e.closed_trade_id=t.closed_trade_id" in text
    assert '"risk_context_full": risk_full' in text
    assert '_load_latest_context(database_url, "trade_risk_context"' not in text


def test_checkpoint_invalidates_on_context_code_and_identity_changes() -> None:
    text = (ROOT / "src/finam_core/analytics/research_symbol_checkpoint.py").read_text()
    assert "ALGORITHM_VERSION" in text
    assert "maximum_governance_event_id" in text
    assert "identity_digest" in text
    assert "md5(string_agg" in text


def test_market_runtime_steps_are_not_suppressed_by_trade_checkpoint() -> None:
    text = (ROOT / "src/scripts/research_pipeline_orchestrator.py").read_text()
    assert "market_post_steps + (trade_post_steps if changed > 0 else [])" in text


def test_new_paper_snapshot_captures_direct_governance_lineage() -> None:
    text = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert '"governance_event": governance_lineage' in text
    assert "SELECT id, created_at, portfolio_heat_status" in text
    assert "PortfolioGovernanceRepository(database_url).save" in text
