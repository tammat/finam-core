import pytest

from risk.risk_config import RiskConfig
from risk.pre_trade_risk_engine import PreTradeRiskEngine


def build_engine(trading_enabled=True):
    config = RiskConfig(
        max_risk_per_trade=0.01,            # 1% equity
        max_total_exposure=100_000,
        daily_loss_limit=5_000,
        max_position_per_symbol=50_000,
        allowed_symbols={"NG", "BR"},
        trading_enabled=trading_enabled,
    )
    return PreTradeRiskEngine(config)


# --- max_risk_per_trade ---

def test_max_risk_per_trade_exceeded():
    engine = build_engine()

    decision = engine.evaluate(
        symbol="NG",
        side="BUY",
        qty=1,
        price=2_000,  # 2000 notional, equity=100k → limit=1000
        equity=100_000,
        current_exposure=0,
        current_position_notional=0,
        daily_realized_pnl=0,
    )

    assert not decision.approved
    assert decision.reason == "max_risk_per_trade_exceeded"


def test_max_risk_per_trade_boundary_allowed():
    engine = build_engine()

    decision = engine.evaluate(
        symbol="NG",
        side="BUY",
        qty=1,
        price=1_000,  # exactly 1% of 100k
        equity=100_000,
        current_exposure=0,
        current_position_notional=0,
        daily_realized_pnl=0,
    )

    assert decision.approved


# --- total exposure ---

def test_total_exposure_exceeded():
    engine = build_engine()

    decision = engine.evaluate(
        symbol="NG",
        side="BUY",
        qty=1,
        price=2_000,
        equity=100_000,
        current_exposure=99_000,
        current_position_notional=0,
        daily_realized_pnl=0,
    )

    assert not decision.approved
    assert decision.reason == "max_total_exposure_exceeded"


# --- per symbol position ---

def test_max_position_per_symbol_exceeded():
    engine = build_engine()

    decision = engine.evaluate(
        symbol="NG",
        side="BUY",
        qty=1,
        price=10_000,
        equity=100_000,
        current_exposure=0,
        current_position_notional=45_000,
        daily_realized_pnl=0,
    )

    assert not decision.approved
    assert decision.reason == "max_position_per_symbol_exceeded"


# --- daily loss ---

def test_daily_loss_limit_exceeded():
    engine = build_engine()

    decision = engine.evaluate(
        symbol="NG",
        side="BUY",
        qty=1,
        price=500,
        equity=100_000,
        current_exposure=0,
        current_position_notional=0,
        daily_realized_pnl=-6_000,
    )

    assert not decision.approved
    assert decision.reason == "daily_loss_limit_exceeded"


# --- symbol whitelist ---

def test_symbol_not_allowed():
    engine = build_engine()

    decision = engine.evaluate(
        symbol="USDRUB",
        side="BUY",
        qty=1,
        price=1_000,
        equity=100_000,
        current_exposure=0,
        current_position_notional=0,
        daily_realized_pnl=0,
    )

    assert not decision.approved
    assert decision.reason == "symbol_not_allowed"


# --- trading disabled ---

def test_trading_disabled():
    engine = build_engine(trading_enabled=False)

    decision = engine.evaluate(
        symbol="NG",
        side="BUY",
        qty=1,
        price=100,
        equity=100_000,
        current_exposure=0,
        current_position_notional=0,
        daily_realized_pnl=0,
    )

    assert not decision.approved
    assert decision.reason == "trading_disabled"


# --- valid trade ---

def test_valid_trade():
    engine = build_engine()

    decision = engine.evaluate(
        symbol="NG",
        side="BUY",
        qty=1,
        price=500,
        equity=100_000,
        current_exposure=10_000,
        current_position_notional=10_000,
        daily_realized_pnl=0,
    )

    assert decision.approved
    assert decision.reason is None