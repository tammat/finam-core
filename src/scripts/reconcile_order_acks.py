# -*- coding: utf-8 -*-
"""
CLI: сверка order_acks из PostgreSQL с текущими заявками брокера Finam.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.reconciliation.broker_order_reconciliation import (
    BrokerOrderReconciliationService,
    BrokerOrderState,
)
from finam_core.reconciliation.order_ack_repository import OrderAckRepository

# Русский комментарий: используем тот же env-файл, что и systemd service.
load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)


def _dec_to_float(value) -> float:
    try:
        if value is None:
            return 0.0
        if hasattr(value, "value"):
            return float(value.value or 0.0)
        return float(value)
    except Exception:
        return 0.0


def _side_to_text(value) -> str:
    text = str(value)
    if text == "1":
        return "BUY"
    if text == "2":
        return "SELL"
    return text.upper()


def _status_to_text(value) -> str:
    return str(value or "UNKNOWN")


def _broker_order_to_state(order) -> BrokerOrderState:
    nested_order = getattr(order, "order", None)
    source = nested_order if nested_order is not None else order

    return BrokerOrderState(
        order_id=str(getattr(order, "order_id", "") or getattr(order, "id", "") or ""),
        symbol=str(getattr(source, "symbol", "") or ""),
        side=_side_to_text(getattr(source, "side", "")),
        status=_status_to_text(getattr(order, "status", "")),
        qty=_dec_to_float(getattr(order, "initial_quantity", None) or getattr(source, "quantity", None)),
        filled_qty=_dec_to_float(getattr(order, "executed_quantity", None)),
    )


def main() -> int:
    limit = int(os.getenv("ORDER_ACK_RECONCILE_LIMIT", "100"))
    acks = OrderAckRepository().list_recent(limit=limit)

    client = FinamOrdersClient()
    broker_orders = [_broker_order_to_state(o) for o in client.get_orders()]

    service = BrokerOrderReconciliationService(broker_orders)
    issues = []
    for ack in acks:
        issues.extend(service.check_ack(ack))

    print("ORDER_ACK_RECONCILIATION")
    print(f"acks={len(acks)} broker_orders={len(broker_orders)} issues={len(issues)}")

    for issue in issues:
        print(
            f"ORDER_ACK_RECON_ISSUE type={issue.issue_type} "
            f"order_id={issue.order_id} symbol={issue.symbol} reason={issue.reason}"
        )

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
