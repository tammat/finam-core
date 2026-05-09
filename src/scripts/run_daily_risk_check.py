# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from finam_core.risk.daily_risk_tracker import DailyRiskTracker
from finam_core.storage.daily_risk_repository import DailyRiskRepository
from finam_core.notifications.notification_router import NotificationRouter


def main() -> int:
    repo = DailyRiskRepository()
    tracker = DailyRiskTracker()

    equities = repo.load_today_equities()

    state = tracker.calculate(
        equities=equities,
        max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "3.0")),
        max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "10.0")),
    )

    print(
        "DAILY_RISK_STATE "
        f"start={state.start_equity} "
        f"current={state.current_equity} "
        f"peak={state.peak_equity} "
        f"daily_pnl={state.daily_pnl} "
        f"dd={state.drawdown_pct}% "
        f"daily_loss={state.daily_loss_pct}% "
        f"kill={state.kill_switch} "
        f"reason={state.reason}",
        flush=True,
    )

    if state.kill_switch:
        NotificationRouter().send(
            trigger="healthcheck",
            text=(
                "🚨 RISK KILL SWITCH\n"
                f"Reason: {state.reason}\n"
                f"Start equity: {state.start_equity:,.2f}\n"
                f"Current equity: {state.current_equity:,.2f}\n"
                f"Daily P&L: {state.daily_pnl:,.2f}\n"
                f"Drawdown: {state.drawdown_pct:.2f}%\n"
                f"Daily loss: {state.daily_loss_pct:.2f}%"
            ),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
