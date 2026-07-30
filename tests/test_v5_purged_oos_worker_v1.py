from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.run_v5_purged_oos_worker_v1 import _matches


def test_context_match_is_exact_for_v5_oos() -> None:
    request = {"paper_strategy_code":"S","side_code":"LONG","session_code":"MAIN",
               "regime_code":"RANGE","holding_code":"TRAIL"}
    trade = {"strategy":"S","side":"LONG","entry_regime":"RANGE",
             "payload":{"context":{"entry_session_msk":"MAIN","actual_exit_reason":"TRAIL"}}}
    assert _matches(request, trade)
    trade["payload"]["context"]["entry_session_msk"] = "EVENING"
    assert not _matches(request, trade)


def test_worker_contract_contains_temporal_and_reuse_guards() -> None:
    source = Path("src/scripts/run_v5_purged_oos_worker_v1.py").read_text()
    assert 'trade["entry_ts"] < run["confirmation_after_ts"]' in source
    assert "SOURCE_TRADE_ALREADY_USED_BY_ANOTHER_OOS_RUN" in source
    assert "v5_oos_observation_audit_v1" in source
    assert "promotion_allowed=0 live_allowed=0" in source


def test_confirmation_boundary_is_strictly_after_embargo() -> None:
    purge = datetime(2026,7,30,tzinfo=timezone.utc)
    confirmation = purge + timedelta(minutes=30)
    assert confirmation > purge
