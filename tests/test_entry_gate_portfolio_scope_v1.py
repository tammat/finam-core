from finam_core.runtime.entry_gate_coordinator import EntryGateCoordinator


class _Allowed:
    allowed = True
    reason = "ok"


class _TradeGate:
    def cooldown_allows(self, **_kwargs):
        return _Allowed()

    def trade_limit_allows(self, *_args, **_kwargs):
        return _Allowed()


class _TrendGate:
    def allow_entry(self, **_kwargs):
        return _Allowed()


class _RuntimeControl:
    def __init__(self):
        self.portfolio_scope = None

    def allow_paper(self, *, symbol, qty, strategy, portfolio_scope=None):
        self.portfolio_scope = portfolio_scope
        return True, qty, "runtime_control_scope_bootstrap"


class _RegimeControlMustNotRun:
    def allow_regime(self, **_kwargs):
        raise AssertionError("legacy regime control must not gate a new research scope")


def main() -> None:
    runtime_control = _RuntimeControl()
    coordinator = EntryGateCoordinator(
        trade_gate_service=_TradeGate(),
        runtime_control_service=runtime_control,
        trend_gate_service=_TrendGate(),
        regime_runtime_control_service=_RegimeControlMustNotRun(),
    )

    decision = coordinator.allow_entry(
        symbol="BRQ6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        strategy_side="BUY",
        expected_side="BUY",
        qty=1.0,
        price=70.0,
        portfolio_scope="FRESH_V5_CONFIRMED_FUTURES",
    )

    assert decision.allowed is True
    assert runtime_control.portfolio_scope == "FRESH_V5_CONFIRMED_FUTURES"
    assert "regime_control_scope_bootstrap" in decision.reason
    print("VERDICT=TEST_ENTRY_GATE_PORTFOLIO_SCOPE_V1_OK")


if __name__ == "__main__":
    main()
