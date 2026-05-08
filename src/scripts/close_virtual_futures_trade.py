# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse

from finam_core.analytics.trade_outcome_reporter import TradeOutcomeReporter
from finam_core.notifications.trade_signal_notifier import TradeSignalNotifier
from finam_core.storage.virtual_signal_trade_repository import VirtualSignalTradeRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--exit-price", type=float, required=True)
    parser.add_argument("--reason", default="manual_close")
    args = parser.parse_args()

    repo = VirtualSignalTradeRepository()
    trade = repo.get_latest_open_trade(args.symbol)

    if not trade:
        raise SystemExit(f"OPEN_VIRTUAL_TRADE_NOT_FOUND symbol={args.symbol}")

    reporter = TradeOutcomeReporter(TradeSignalNotifier())

    outcome = reporter.analyze(
        symbol=trade["symbol"],
        side=trade["side"],
        entry_price=float(trade["entry_price"]),
        exit_price=float(args.exit_price),
        qty=float(trade["qty"]),
        stop_loss=float(trade["stop_loss"]),
        take_profit=float(trade["take_profit"]),
        reason=args.reason,
    )

    repo.close_trade(
        trade_id=int(trade["id"]),
        exit_price=float(args.exit_price),
        close_reason=args.reason,
        pnl=outcome.pnl,
        r_multiple=outcome.r_multiple,
    )

    reporter.send_outcome(outcome)

    print(
        f"VIRTUAL_TRADE_CLOSED id={trade['id']} symbol={outcome.symbol} side={outcome.side} "
        f"entry={outcome.entry_price} exit={outcome.exit_price} "
        f"pnl={outcome.pnl} r={outcome.r_multiple} result={outcome.result}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
