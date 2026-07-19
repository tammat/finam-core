from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.run_autonomous_edge_search_cycle_v1 import session_freshness_minutes


def test_autonomous_cycle_searches_and_promotes_only_to_forward() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert "pg_try_advisory_lock" in source
    assert "build_edge_regime_hypothesis_discovery_v2.py" in source
    assert "build_walkforward_edge_search_v3.py" in source
    assert "promote_regime_oos_to_canonical_v1.py" in source
    assert "admit_oos_forward_clean_cohort_v1.py" in source
    assert "build_profit_funnel_shadow_paper_admission_v2.py" in source
    assert "build_profit_funnel_paper_runtime_admission_v2.py" not in source
    assert '"REAL_TRADING_ENABLED": "0"' in source
    assert "live_allowed=0" in source


def test_autonomous_cycle_has_auditable_log_wrapper() -> None:
    wrapper = Path("deploy/run-autonomous-edge-search-v1.sh").read_text()
    assert "set -euo pipefail" in wrapper
    assert "autonomous-edge-search-v1.log" in wrapper


def test_search_freshness_respects_market_session() -> None:
    msk = ZoneInfo("Europe/Moscow")
    assert session_freshness_minutes(datetime(2026, 7, 17, 12, tzinfo=msk)) == 15
    assert session_freshness_minutes(datetime(2026, 7, 17, 1, tzinfo=msk)) == 720
    assert session_freshness_minutes(datetime(2026, 7, 20, 8, tzinfo=msk)) == 4320


def test_cycle_records_truthful_progress_and_outcome() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    migration = Path("sql/analytics/069_edge_search_cycle_status_v1.sql").read_text()
    assert 'outcome = "NO_CURRENT_MARKETS"' in source
    assert '"PASS_FOUND" if passes else "NO_PASS"' in source
    assert "combinations_evaluated" in source
    assert "progress_pct" in source
    assert "NO_CURRENT_MARKETS" in migration


def test_cycle_skips_unchanged_market_data_unless_operator_forces_it() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    migration = Path("sql/analytics/070_edge_search_data_watermark_v1.sql").read_text()
    worker = Path("src/marketcore/action/command_worker_v2.py").read_text()
    assert "market_data_watermark" in source
    assert "EDGE_SEARCH_DATA_UNCHANGED" in source
    assert 'os.getenv("EDGE_SEARCH_FORCE", "0")' in source
    assert "'SKIPPED'" in migration
    assert 'env["EDGE_SEARCH_FORCE"] = "1"' in worker
def test_cycle_releases_snapshot_transaction_before_executors() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text(encoding="utf-8")
    assert "releasing the snapshot transaction" in source
    assert "lock_connection.commit()" in source


def test_cycle_heartbeats_while_executor_is_running() -> None:
    source = Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text(encoding="utf-8")
    assert "subprocess.Popen" in source
    assert "communicate(timeout=15)" in source
    assert "heartbeat_connection" in source
