from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.build_strategy_execution_runner_v1 import Bar, build_trades


ROOT = Path(__file__).resolve().parents[1]


def bars(with_quotes: bool = False) -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Bar(
            start + timedelta(minutes=5 * index),
            100.0 + index,
            100000.0,
            best_bid=99.9 + index if with_quotes else None,
            best_ask=100.1 + index if with_quotes else None,
        )
        for index in range(100)
    ]


def run(policy: dict | None = None) -> dict:
    return {
        "strategy_code": "BREAKOUT_V1",
        "parameter_json": {
            "lookback": 20,
            "hold": 5,
            "commission": 0.0,
            "execution_policy": {
                "signal_latency_bars": 1,
                "max_participation_rate": 0.01,
                "minimum_fill_ratio": 0.25,
                "target_notional_rub": 1000.0,
                "fallback_spread_bps": 10.0,
                "impact_bps_at_max_participation": 4.0,
                "lot_size": 1.0,
                "contract_multiplier": 1.0,
                "quote_source": "EMPIRICAL_P90_MICROSTRUCTURE",
                "contract_spec_source": "TEST_SPEC",
                **(policy or {}),
            },
        },
    }


def test_signal_executes_on_next_bar_and_costs_are_adverse() -> None:
    result = build_trades(run(), bars())
    assert result
    trade = result[0]
    assert trade.entry_ts == bars()[21].ts
    assert trade.latency_bars == 1
    assert trade.spread_cost > 0 and trade.impact_cost > 0
    assert trade.net_pnl < trade.gross_pnl
    assert trade.entry_price > bars()[21].close


def test_historical_bid_ask_is_preferred_when_available() -> None:
    trade = build_trades(run(), bars(with_quotes=True))[0]
    assert trade.quote_source == "HISTORICAL_BID_ASK"
    assert trade.entry_price > bars(with_quotes=True)[21].best_ask


def test_participation_limit_can_reject_unfillable_trade() -> None:
    constrained = run({"research_equity_rub":100000000.0,"max_gross_leverage":3.0,
                       "max_position_share":1.0,"minimum_fill_ratio":0.25})
    assert build_trades(constrained, bars()) == []


def test_futures_underlying_volume_is_not_quantity_step() -> None:
    futures=run({"target_notional_rub":100000.0,"research_equity_rub":100000.0,
                 "max_gross_leverage":3.0,"max_position_share":0.35,
                 "quantity_step":1.0,"underlying_units":100.0,
                 "contract_multiplier":7831.81})
    futures_bars=[Bar(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=5*index),
                      3.0+index*0.01,100000.0) for index in range(100)]
    result=build_trades(futures,futures_bars)
    assert result
    assert result[0].quantity >= 1


def test_policy_and_trade_audit_are_db_versioned() -> None:
    sql = (ROOT / "sql/analytics/092_realistic_execution_model_v1.sql").read_text()
    runner = (ROOT / "src/scripts/build_strategy_execution_runner_v1.py").read_text()
    evaluator = (ROOT / "src/scripts/evaluate_edge_methodology_contract_v1.py").read_text()
    assert "REALISTIC_EXECUTION_V1" in sql
    assert "EXECUTION_SIMULATION_POLICY_IMMUTABLE" in sql
    for field in ("fill_ratio", "spread_cost", "impact_cost", "latency_bars", "quote_source"):
        assert field in sql and field in runner
    assert '"execution_policy"' in evaluator
    assert "contract_spec_coverage" in evaluator
