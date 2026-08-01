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
