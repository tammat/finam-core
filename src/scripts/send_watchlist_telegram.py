# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.storage.dynamic_watchlist_repository import DynamicWatchlistRepository
from finam_core.notifications.telegram_notifier import TelegramNotifier


def main() -> int:
    repo = DynamicWatchlistRepository()
    rows = repo.load_watchlist()[:5]

    if not rows:
        print("WATCHLIST_TELEGRAM_SKIP reason=empty_watchlist")
        return 0

    lines = ["📡 Market Radar TOP-5"]

    for i, r in enumerate(rows, start=1):
        lines.append(
            f"{i}. {r['symbol']} {r.get('name') or ''}\n"
            f"   {r.get('direction')} | score={r.get('score'):.2f} | "
            f"RS={r.get('relative_strength'):.2f}%\n"
            f"   {r.get('portfolio_status')} → {r.get('portfolio_action')}"
        )

    text = "\n".join(lines)

    TelegramNotifier().send(text)

    print("WATCHLIST_TELEGRAM_SENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
