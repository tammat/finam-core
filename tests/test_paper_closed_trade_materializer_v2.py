from pathlib import Path
from datetime import datetime, timezone
import importlib.util


ROOT = Path(__file__).resolve().parents[1]


def test_materializer_writes_both_canonical_and_analytics_tables() -> None:
    text = (ROOT / "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py").read_text()
    assert "def upsert_canonical_trades" in text
    assert "paper_fill_materializer_v2" in text
    assert "materialized_trade_id" in text
    assert "NULLIF(t.payload->>'strategy','')" in text
    assert "upsert_trades(conn, trades)" in text
    assert "upsert_canonical_trades(conn, trades, legacy_cutoff, context_activated_at)" in text
    assert "paper_trade_context_capture_state_v2" in text
    assert "portfolio_scope" in text
    assert "legacy_cutoff" in text
    assert "refresh_canonical_attribution" in text
    assert '"planned_exit_rule": planned_exit_rule' in text
    assert '"actual_exit_reason": actual_exit_reason' in text
    assert '"entry_stop_price": entry.get("stop_price")' in text
    assert '"entry_take_price": entry.get("take_price")' in text
    assert 'exit_rule = "TIME_EXIT"' in text
    assert '"stall_exit" in reason_key' in text
    assert 'exit_rule = "TRAILING"' in text
    assert 'exit_rule = "TARGET"' in text
    assert 'exit_rule = "STOP"' in text
    assert '"regime_trend": regime_trend' in text
    assert '"regime_vol": regime_vol' in text
    assert '"side": entry_side' in text
    assert "resolve_pnl_unit_spec" in text
    assert "PNL_UNITS_V2_RUB" in text
    assert "gross_pnl_rub" in text
    assert "gross_pnl=%(pnl_points)s" in text
    assert "net_pnl=%(net_pnl)s" in text
    assert "PNL_UNIT_FUTURES_SPEC_MISSING" in text
    assert "IS DISTINCT FROM 'PNL_UNITS_V2_RUB'" in text


def test_materializer_does_not_inherit_trading_symbol_scope() -> None:
    text = (ROOT / "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py").read_text()
    assert 'os.getenv("SYMBOL")' not in text
    assert 'os.getenv("SYMBOLS")' not in text
    assert 'os.getenv("PAPER_MATERIALIZER_SYMBOL")' in text
    assert 'os.getenv("PAPER_MATERIALIZER_SYMBOLS")' in text


def test_materializer_never_offsets_positions_across_portfolio_scopes() -> None:
    text = (ROOT / "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py").read_text()
    assert "COALESCE(f.portfolio_scope, sf.portfolio_scope) AS fill_scope" in text
    assert "open_longs_by_scope" in text
    assert "open_shorts_by_scope" in text
    assert 'fill_scope = f.get("fill_scope")' in text
    assert '"portfolio_scope": fill_scope' in text
    assert 't.get("portfolio_scope") or resolve_scope_at_entry' in text


def test_reconstruct_keeps_legacy_and_v4_inventory_separate() -> None:
    path = ROOT / "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py"
    spec = importlib.util.spec_from_file_location("paper_materializer", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def fill(fill_id: str, side: str, scope: str | None, minute: int) -> dict:
        return {
            "fill_id": fill_id,
            "side": side,
            "fill_scope": scope,
            "qty": 1,
            "price": 100 if side == "BUY" else 101,
            "ts": datetime(2026, 7, 22, 4, minute, tzinfo=timezone.utc),
            "commission": 0,
        }

    trades = module.reconstruct(
        "SBER@MISX",
        [
            fill("legacy-entry", "BUY", None, 0),
            fill("v4-entry", "BUY", "FRESH_V4_REGIME_EQUITY", 1),
            fill("v4-exit", "SELL", "FRESH_V4_REGIME_EQUITY", 2),
        ],
    )

    assert len(trades) == 1
    assert trades[0]["entry_fill_id"] == "v4-entry"
    assert trades[0]["exit_fill_id"] == "v4-exit"
    assert trades[0]["portfolio_scope"] == "FRESH_V4_REGIME_EQUITY"


def test_scheduler_runs_materializer_with_apply_and_foreground_priority() -> None:
    text = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"PAPER_CLOSED_TRADE_MATERIALIZER_V2"' in text
    assert '["--apply"]' in text
    assert 'EXECUTOR_NICE = {"PAPER_CLOSED_TRADE_MATERIALIZER_V2": 0}' in text


def test_migration_is_idempotent_and_scheduled() -> None:
    text = (ROOT / "sql/analytics/136_paper_closed_trade_materializer_v2.sql").read_text()
    assert "paper_closed_trade_identity_v2" in text
    assert "PRIMARY KEY" in text
    assert "ON CONFLICT(job_code) DO UPDATE" in text
    assert "PAPER_CLOSED_TRADE_MATERIALIZER_V2" in text
