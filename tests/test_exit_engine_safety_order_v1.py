from finam_core.strategy.exit_engine import ExitEngine


def test_long_protective_stop_precedes_time_exit():
    decision = ExitEngine(max_bars_in_trade=20).evaluate(
        side="BUY", entry_price=100, current_price=98, atr=1,
        bars_held=20, current_stop=99,
    )
    assert decision.should_exit
    assert decision.reason == "stop_loss_long"


def test_short_protective_stop_precedes_time_exit():
    decision = ExitEngine(max_bars_in_trade=20).evaluate(
        side="SELL", entry_price=100, current_price=102, atr=1,
        bars_held=20, current_stop=101,
    )
    assert decision.should_exit
    assert decision.reason == "stop_loss_short"
