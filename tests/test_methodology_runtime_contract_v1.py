from pathlib import Path

from finam_core.runtime.research_contract_key_v1 import normalize_research_contract_key_v1
from finam_core.storage.trade_context_guard_v1 import TradeContextGuardV1


ROOT = Path(__file__).resolve().parents[1]


def test_br_contract_key_is_canonical() -> None:
    key = normalize_research_contract_key_v1(
        symbol="BRQ6@RTSX",strategy="br_conservative_breakout",timeframe="LIVE",
        side="LONG",session_name="EUROPE_OVERLAP",regime="TREND_UP_HIGH_VOL",
    )
    assert key.normalized_symbol == "BR_CONT"
    assert key.timeframe == "M5"
    assert key.side == "BUY"
    assert key.regime_code == "trend_up_high_vol"


def test_storage_guard_cannot_persist_br_live_timeframe() -> None:
    decision = TradeContextGuardV1().normalize(
        symbol="BRQ6@RTSX",strategy="BR_CONSERVATIVE_BREAKOUT",timeframe="LIVE",
        continuous_symbol="BR_CONT",payload={},
    )
    assert decision.allowed
    assert decision.timeframe == "M5"
    assert decision.continuous_symbol == "BR_CONT"


def test_db_quota_and_clean_cohort_are_migrated() -> None:
    sql = (ROOT / "sql/analytics/162_methodology_runtime_contract_v1.sql").read_text()
    assert "paper_research_quota_policy_v1" in sql
    assert "paper_research_quota_reservation_v1" in sql
    assert "BR_RESEARCH_PAPER" in sql
    assert "MICROSTRUCTURE_CLEAN_V4" in sql
    assert "min_microstructure_coverage numeric NOT NULL DEFAULT 0.80" in sql


def test_pipeline_uses_one_db_backed_trade_gate() -> None:
    source = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    constructor = source[source.index("class PaperTradingPipeline"):source.index("def _log_dedup",source.index("class PaperTradingPipeline"))]
    assert constructor.count("self.trade_gate_service = TradeGateService(") == 1
    assert 'connection_factory=getattr(self.pg_logger, "_connect", None)' in source
    assert "_account_trade_after_fill_v1(intent)" in source


def test_m15_rebuild_is_idempotent_and_uses_complete_m5_buckets() -> None:
    source = (ROOT / "src/scripts/rebuild_m15_from_m5_v1.py").read_text()
    assert "HAVING count(*)=3" in source
    assert "max(b.ts)-min(b.ts)=interval '10 minutes'" in source
    assert "ON CONFLICT(symbol,timeframe,ts) DO UPDATE" in source
    assert "synthetic_futures_backfill_v1" in source


def test_scheduler_limits_cpu_by_market_window() -> None:
    source = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "def research_cpu_limit" in source
    assert '"OMP_NUM_THREADS": str(cpu_limit)' in source
    assert '"0" if cpu_limit == 1 else "0,1"' in source
    assert "def resource_gate" in source
    assert "HEAVY_EXECUTORS" in source


def test_microstructure_label_separates_quote_match_from_verified_cohort() -> None:
    source = (ROOT / "src/scripts/build_session_execution_edge_v1.py").read_text()
    assert '"QUOTE_MATCHED"' in source
    assert '"MICROSTRUCTURE_COHORT_VERIFIED"' in source
    assert "item[\"matched\"] >= item[\"required_matched_trades\"]" in source
