from __future__ import annotations

from datetime import datetime, timezone

import finam_core.risk.portfolio_risk_gate as module


class FakeCursor:
    def __init__(self, config, state, degradation):
        self.config = config
        self.state = state
        self.degradation = degradation
        self.result = None
        self.inserts = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        if "FROM analytics.risk_config_v2" in normalized:
            self.result = self.config
        elif "FROM public.portfolio_risk_state" in normalized:
            self.result = self.state
        elif "FROM analytics.strategy_degradation_state_v1" in normalized:
            self.result = self.degradation
        elif "INSERT INTO analytics.risk_control_decision_v2" in normalized:
            self.inserts.append(params)
            self.result = None

    def fetchone(self):
        return self.result


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self):
        return self._cursor


def run_gate(monkeypatch, *, config, state, qty=4, degradation=None, **metrics):
    if degradation is None:
        degradation = (100, 1.0, 1.5, "NORMAL", 1.0, "within_limits", datetime.now(timezone.utc))
    cursor = FakeCursor(config, state, degradation)
    monkeypatch.setattr(module.psycopg, "connect", lambda _dsn: FakeConnection(cursor))
    decision = module.PortfolioRiskGate("postgresql://test").check(
        "BRQ6@RTSX",
        signal_id="signal-1",
        strategy_family="BREAKOUT",
        requested_quantity=qty,
        equity_rub=metrics.get("equity_rub", 100_000),
        peak_equity_rub=metrics.get("peak_equity_rub", 100_000),
        gross_exposure_rub=metrics.get("gross_exposure_rub", 20_000),
        symbol_exposure_rub=metrics.get("symbol_exposure_rub", 5_000),
        used_margin_rub=metrics.get("used_margin_rub", 10_000),
        daily_pnl_rub=metrics.get("daily_pnl_rub", 0),
        drawdown_rub=metrics.get("drawdown_rub", 0),
        entry_price=metrics.get("entry_price", 100),
        stop_price=metrics.get("stop_price", 99),
        contract_multiplier=metrics.get("contract_multiplier", 1),
    )
    return decision, cursor


def test_missing_state_blocks_and_is_audited(monkeypatch):
    decision, cursor = run_gate(
        monkeypatch,
        config=(True, 0.60, 0.50, 900, 0.02, 0.03, 0.10, 1.00, 0.65, 0.01),
        state=None,
    )
    assert decision.decision_code == "BLOCK"
    assert decision.allowed is False
    assert decision.approved_quantity == 0
    assert cursor.inserts


def test_elevated_cluster_reduces_quantity(monkeypatch):
    decision, cursor = run_gate(
        monkeypatch,
        config=(True, 0.60, 0.50, 900, 0.02, 0.03, 0.10, 1.00, 0.65, 0.01),
        state=("ELEVATED", 0.45, "cluster_share_elevated", datetime.now(timezone.utc)),
        qty=6,
    )
    assert decision.decision_code == "REDUCE"
    assert decision.allowed is True
    assert decision.approved_quantity == 3
    assert cursor.inserts


def test_normal_cluster_allows_requested_quantity(monkeypatch):
    decision, _cursor = run_gate(
        monkeypatch,
        config=(True, 0.60, 0.50, 900, 0.02, 0.03, 0.10, 1.00, 0.65, 0.01),
        state=("NORMAL", 0.20, "within_limits", datetime.now(timezone.utc)),
        qty=2,
    )
    assert decision.decision_code == "ALLOW"
    assert decision.allowed is True
    assert decision.approved_quantity == 2


def test_unassessed_strategy_is_limited_to_one_unit(monkeypatch):
    decision, _cursor = run_gate(
        monkeypatch,
        config=(True, 0.60, 0.50, 900, 0.02, 0.03, 0.10, 1.00, 0.65, 0.01),
        state=("NORMAL", 0.20, "within_limits", datetime.now(timezone.utc)),
        degradation=(),
        qty=4,
    )
    assert decision.decision_code == "REDUCE"
    assert decision.allowed is True
    assert decision.approved_quantity == 1


def test_daily_loss_limit_blocks(monkeypatch):
    decision, _cursor = run_gate(
        monkeypatch,
        config=(True, 0.60, 0.50, 900, 0.02, 0.03, 0.10, 1.00, 0.65, 0.01),
        state=("NORMAL", 0.20, "within_limits", datetime.now(timezone.utc)),
        daily_pnl_rub=-2_100,
    )
    assert decision.decision_code == "BLOCK"
    assert decision.reason == "daily_loss_limit_exceeded"


def test_symbol_exposure_limit_blocks(monkeypatch):
    decision, _cursor = run_gate(
        monkeypatch,
        config=(True, 0.60, 0.50, 900, 0.02, 0.03, 0.10, 1.00, 0.65, 0.01),
        state=("NORMAL", 0.20, "within_limits", datetime.now(timezone.utc)),
        symbol_exposure_rub=10_001,
    )
    assert decision.decision_code == "BLOCK"
    assert decision.reason == "symbol_exposure_limit_exceeded"
