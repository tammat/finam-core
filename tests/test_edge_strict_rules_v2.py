import json
from pathlib import Path

from finam_core.execution.edge_gate_strict_mode_v1 import EdgeGateStrictModeV1


ROOT = Path(__file__).resolve().parents[1]


def _gate(tmp_path: Path) -> EdgeGateStrictModeV1:
    config = tmp_path / "strict.json"
    config.write_text(
        json.dumps(
            {
                "enabled": True,
                "strict_expectancy_threshold": 0,
                "strict_min_closed_trades": 30,
                "sources": [],
            }
        )
    )
    gate = EdgeGateStrictModeV1(config)
    gate._db_rows = [
        {
            "normalized_symbol": "BR_CONT",
            "strategy": "BR_CONSERVATIVE_BREAKOUT",
            "entry_side": "BUY",
            "session_name": "EUROPE_OVERLAP",
            "timeframe": "M5",
            "regime_code": "trend_up_high_vol",
            "closed_trades": 31,
            "expectancy_points": 0.12,
            "microstructure_coverage_ratio": 0.85,
            "rule_action": "ALLOW",
        },
        {
            "normalized_symbol": "SBERP@MISX",
            "strategy": "VOLATILITY_BREAKOUT_EQUITY",
            "entry_side": "BUY",
            "session_name": "EUROPE_OVERLAP",
            "timeframe": "M5",
            "regime_code": "trend_up_high_vol",
            "closed_trades": 8,
            "expectancy_points": 0.4,
            "microstructure_coverage_ratio": 0.90,
            "rule_action": "INSUFFICIENT_DATA",
        },
    ]
    return gate


def test_rule_matches_instrument_strategy_side_and_session(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    decision = gate.evaluate(
        symbol="BRQ6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        side="BUY",
        session_name="EUROPE_OVERLAP",timeframe="LIVE",regime="trend_up_high_vol",
        hour_msk=12,
    )
    assert decision.allowed is True
    assert decision.matched_symbol == "BR_CONT"
    assert decision.matched_strategy == "BR_CONSERVATIVE_BREAKOUT"

    wrong_strategy = gate.evaluate(
        symbol="BRQ6@RTSX",
        strategy="OTHER_STRATEGY",
        side="BUY",
        session_name="EUROPE_OVERLAP",timeframe="M5",regime="trend_up_high_vol",
        hour_msk=12,
    )
    assert wrong_strategy.allowed is False
    assert wrong_strategy.reason == "strict_mode_no_match"


def test_low_sample_remains_blocked_by_strict_rule(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    decision = gate.evaluate(
        symbol="SBERP@MISX",
        strategy="VOLATILITY_BREAKOUT_EQUITY",
        side="BUY",
        session_name="EUROPE_OVERLAP",timeframe="M5",regime="trend_up_high_vol",
        hour_msk=12,
    )
    assert decision.allowed is False
    assert decision.reason == "strict_mode_low_sample"


def test_rule_builder_and_scheduler_are_db_driven() -> None:
    migration = (ROOT / "sql/analytics/134_edge_strict_rules_v2.sql").read_text()
    builder = (ROOT / "src/scripts/build_edge_strict_rules_v2.py").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert "edge_strict_rule_v2" in migration
    assert "EDGE_STRICT_RULE_BUILD_V2" in scheduler
    assert "public.closed_trades" in builder
    assert "next_is_exit" not in builder
    assert "expectancy_after_costs" in builder
    assert "runtime_changed=0" in builder
    assert "real_trading_enabled=0" in builder


def test_allow_requires_clean_microstructure_coverage(tmp_path: Path) -> None:
    gate = _gate(tmp_path)
    gate._db_rows[0]["microstructure_coverage_ratio"] = 0.799
    decision = gate.evaluate(
        symbol="BRQ6@RTSX",strategy="BR_CONSERVATIVE_BREAKOUT",side="BUY",
        session_name="EUROPE_OVERLAP",timeframe="LIVE",regime="trend_up_high_vol",
    )
    assert decision.allowed is False
    assert decision.reason == "strict_mode_microstructure_coverage_low"


def test_cluster_gate_uses_only_nonzero_real_positions() -> None:
    pipeline = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    cluster = pipeline[pipeline.index("# === CORRELATION FILTER ===") : pipeline.index("if intent.get(\"price\") is None", pipeline.index("# === CORRELATION FILTER ==="))]
    assert "abs(position_qty) <= 1e-12" in cluster
    assert "position_symbol) == str(intent.get" in cluster
    assert "_runtime_symbol_reload_if_due(active_symbols)" not in cluster


def test_evidence_accumulation_is_paper_only() -> None:
    pipeline = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert "PIPE_STRICT_GATE_EVIDENCE_ACCUMULATION_V2" in pipeline
    assert 'os.getenv("REAL_TRADING_ENABLED", "0") != "1"' in pipeline
    assert 'os.getenv("EXECUTION_ENABLED", "0") != "1"' in pipeline


def test_legacy_br_bypass_cannot_override_confirmed_negative_edge() -> None:
    pipeline = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    block = pipeline[
        pipeline.index("br_paper_bypass = (") :
        pipeline.index("evidence_accumulation_bypass = (")
    ]
    assert "strict_mode_no_match" in block
    assert "strict_mode_low_sample" in block
    assert "strict_mode_non_positive_expectancy" not in block
