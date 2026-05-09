# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from finam_core.portfolio.portfolio_mtm_service import PortfolioMtmService
from finam_core.notifications.telegram_notifier import TelegramNotifier


ALERT_THRESHOLD = float(
    os.getenv("MARGIN_UTILIZATION_ALERT_PCT", "65")
)

BASE_EQUITY = float(
    os.getenv("PORTFOLIO_BASE_EQUITY", "366337.96")
)


def main() -> int:
    svc = PortfolioMtmService()
    notifier = TelegramNotifier()

    snap = svc.calculate(base_equity=BASE_EQUITY)
    svc.save_snapshot(snap)

    print(
        "PORTFOLIO_MTM_OK "
        f"equity={snap.live_equity} "
        f"unrealized={snap.unrealized_pnl} "
        f"margin_used={snap.used_margin} "
        f"free_margin={snap.free_margin} "
        f"utilization={snap.margin_utilization_pct}%"
    )

    if snap.margin_utilization_pct >= ALERT_THRESHOLD:
        notifier.send(
            "\n".join([
                "⚠️ MARGIN ALERT",
                f"Equity: {snap.live_equity:,.2f} RUB",
                f"Used margin: {snap.used_margin:,.2f} RUB",
                f"Free margin: {snap.free_margin:,.2f} RUB",
                f"Margin utilization: {snap.margin_utilization_pct:.2f}%",
                f"Positions: {snap.positions_count}",
            ])
        )

        print("PORTFOLIO_MTM_TELEGRAM_ALERT_SENT")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
