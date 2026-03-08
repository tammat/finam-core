# tests/test_exposure_rule_limits.py
from types import SimpleNamespace

from finam_core.domain.risk.rules.exposure_rule import ExposureRule


def _allowed(decision) -> bool:
    # RiskDecision может иметь разные флаги в разных версиях
    for flag in ("allowed", "is_allowed", "ok", "approved", "pass_"):
        if hasattr(decision, flag):
            return bool(getattr(decision, flag))
    return bool(decision)


def _reason(decision):
    for attr in ("reason", "reasons", "message", "messages", "violations", "code"):
        if hasattr(decision, attr):
            return getattr(decision, attr)
    return None


def test_exposure_rule_percent_limits():
    # 150% of 100_000 = 150_000 ; 20% = 20_000
    rule = ExposureRule(max_total_exposure=150.0, max_symbol_exposure=20.0)

    ctx = SimpleNamespace(
        starting_capital=100_000.0,
        total_exposure=0.0,
        current_symbol_exposure=0.0,
        trade_value=10_000.0,
    )

    dec = rule.evaluate(ctx)
    assert _allowed(dec) is True
    assert _reason(dec) in (None, "", [])


def test_exposure_rule_fraction_limits():
    # 0.5 means 50% of starting_capital
    rule = ExposureRule(max_total_exposure=0.5, max_symbol_exposure=0.2)

    ctx = SimpleNamespace(
        starting_capital=100_000.0,
        total_exposure=49_000.0,
        current_symbol_exposure=19_000.0,
        trade_value=2_000.0,
    )

    dec = rule.evaluate(ctx)
    assert _allowed(dec) is False
    assert _reason(dec) in ("max_total_exposure_exceeded", "max_symbol_exposure_exceeded")