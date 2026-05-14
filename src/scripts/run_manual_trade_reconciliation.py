# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import psycopg2

from finam_core.reconciliation.manual_trade_reconciliation import ManualTradeReconciliation
from finam_core.reconciliation.manual_position_snapshot_repository import ManualPositionSnapshotRepository
from finam_core.notifications.telegram_notifier import TelegramNotifier
from finam_core.notifications.manual_position_pnl_sender import send_manual_position_pnl_alert
from finam_core.reconciliation.manual_position_pnl_analyzer import analyze_position


def build_finam_client():
    """
    Русский комментарий:
    Подключаем существующий Finam client проекта.
    Если имя класса/модуля отличается — адаптируем после grep.
    """
    try:
        from finam_core.infra.finam.client import FinamClient
        return FinamClient()
    except Exception as exc:
        raise RuntimeError(
            f"Не удалось создать FinamClient: {type(exc).__name__}: {exc}"
        ) from exc


class FinamPositionsAdapter:
    """
    Приводит существующий Finam client к интерфейсу:
        get_positions() -> list
    """

    def __init__(self, client):
        self.client = client

    def get_positions(self):
        for method_name in (
            "get_positions",
            "get_portfolio_positions",
            "get_portfolio",
            "portfolio",
        ):
            method = getattr(self.client, method_name, None)
            if method is None:
                continue

            result = method()

            if isinstance(result, dict):
                for key in ("positions", "securities", "assets"):
                    if key in result:
                        return result[key]

            return result

        raise RuntimeError("У FinamClient не найден метод получения позиций")


def main() -> None:
    conn = psycopg2.connect(
        dbname=os.getenv("PGDATABASE", "finam_core"),
        user=os.getenv("PGUSER") or None,
        password=os.getenv("PGPASSWORD") or None,
        host=os.getenv("PGHOST") or None,
        port=os.getenv("PGPORT") or None,
    )

    client = build_finam_client()
    adapter = FinamPositionsAdapter(client)

    reconciliation = ManualTradeReconciliation(adapter)
    positions = reconciliation.get_broker_positions()

    repo = ManualPositionSnapshotRepository(conn)
    saved = repo.save_positions(positions)

    notifier = TelegramNotifier()
    alerts_sent = 0

    for pos in positions:
        pnl = analyze_position(
            symbol=pos.symbol,
            qty=pos.qty,
            average_price=pos.average_price,
            current_price=pos.current_price,
        )

        if pnl is None:
            continue

        if send_manual_position_pnl_alert(notifier, pnl):
            alerts_sent += 1

    print(
        f"MANUAL_RECONCILIATION_OK positions={len(positions)} saved={saved} alerts_sent={alerts_sent}",
        flush=True,
    )

    for p in positions:
        print(
            f"POSITION symbol={p.symbol} qty={p.qty} "
            f"avg={p.average_price} current={p.current_price} pnl={p.unrealized_pnl}",
            flush=True,
        )


if __name__ == "__main__":
    main()
