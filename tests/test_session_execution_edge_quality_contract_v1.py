from datetime import datetime, timezone

import pytest

from scripts.build_session_execution_edge_v1 import (
    Trade,
    VerifiedQuote,
    apply_microstructure_execution,
    trade_fold_passes,
)


def quote(bid: float, ask: float) -> VerifiedQuote:
    return VerifiedQuote(bid, ask, 3, 3, datetime.now(timezone.utc))


def trade(side: str = "BUY") -> Trade:
    entry = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)
    exit_ts = datetime(2026, 7, 20, 10, 1, tzinfo=timezone.utc)
    return Trade(1, side, entry, exit_ts, 100, 101, 1, 0.1, 0.1, 0.8)


def test_buy_is_executed_at_ask_then_bid() -> None:
    source = trade("BUY")
    result = apply_microstructure_execution(
        [source], {source.entry_ts: quote(99, 100), source.exit_ts: quote(102, 103)}
    )
    assert len(result) == 1
    assert result[0].entry_price == 100
    assert result[0].exit_price == 102
    assert result[0].net_pnl == pytest.approx(1.8)
    assert result[0].quote_source == "MICROSTRUCTURE_SNAPSHOT_V1"


def test_sell_is_executed_at_bid_then_ask() -> None:
    source = trade("SELL")
    result = apply_microstructure_execution(
        [source], {source.entry_ts: quote(103, 104), source.exit_ts: quote(100, 101)}
    )
    assert result[0].entry_price == 103
    assert result[0].exit_price == 101
    assert result[0].net_pnl == pytest.approx(1.8)


def test_trade_without_both_quotes_is_excluded() -> None:
    source = trade()
    assert apply_microstructure_execution([source], {source.entry_ts: quote(99, 100)}) == []


def test_empty_verified_cohort_has_no_passed_folds() -> None:
    assert trade_fold_passes([]) == 0
