# -*- coding: utf-8 -*-
"""
CLI: сверка order_acks из PostgreSQL с текущими заявками брокера Finam.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from dotenv import load_dotenv

from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.reconciliation.broker_order_reconciliation import (
    BrokerOrderReconciliationService,
    BrokerOrderState,
)
from finam_core.reconciliation.order_ack_repository import OrderAckRepository
from finam_core.reconciliation.order_reconciliation_logger import OrderReconciliationLogger
from finam_core.reconciliation.broker_order_snapshot_store import BrokerOrderSnapshotStore

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


def _ack_age_hours(ack) -> float:
    # Русский комментарий: возраст ACK нужен, чтобы не подавлять свежие проблемы.
    ts = getattr(ack, "ts", None)
    if ts is None:
        return 0.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0)


def _raw_text(ack) -> str:
    raw = getattr(ack, "raw", None)
    return str(raw or "")


def _raw_number(raw_text: str, field_name: str) -> float | None:
    # Русский комментарий: raw у ACK часто содержит protobuf-text внутри JSON,
    # поэтому парсим устойчиво по строке, не завязываясь на точную структуру.
    patterns = [
        rf"{field_name}[^\n]*value:\s*\"?([0-9.]+)\"?",
        rf"{field_name}[^0-9]+([0-9.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text)
        if match:
            try:
                return float(match.group(1))
            except Exception:
                return None
    return None


def _ack_is_stale_not_filled(ack) -> bool:
    # Русский комментарий:
    # Если заявка старая, принята брокером, но executed_quantity=0,
    # то отсутствие её в текущем списке брокера не является аварией.
    raw = _raw_text(ack)
    age_hours = _ack_age_hours(ack)

    executed = _raw_number(raw, "executed_quantity")
    remaining = _raw_number(raw, "remaining_quantity")

    accepted = "accepted" in raw.lower() or "ORDER_STATUS_NEW" in raw
    not_filled = executed == 0.0
    has_remaining = remaining is None or remaining >= 0.0

    return age_hours >= 24.0 and accepted and not_filled and has_remaining


def _is_non_critical_stale_ack(issue, ack_by_order_id: dict[str, object]) -> bool:
    if getattr(issue, "issue_type", "") != "ACK_MISSING_AT_BROKER":
        return False

    ack = ack_by_order_id.get(str(getattr(issue, "order_id", "") or ""))
    if ack is None:
        return False

    return _ack_is_stale_not_filled(ack)


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
    broker_snapshots_saved = BrokerOrderSnapshotStore().save_many(broker_orders)

    service = BrokerOrderReconciliationService(broker_orders)
    ack_by_order_id = {str(getattr(ack, "order_id", "") or ""): ack for ack in acks}

    critical_issues = []
    non_critical_issues = []

    for ack in acks:
        for issue in service.check_ack(ack):
            if _is_non_critical_stale_ack(issue, ack_by_order_id):
                non_critical_issues.append(issue)
            else:
                critical_issues.append(issue)

    run_id = OrderReconciliationLogger().log_run(
        acks_count=len(acks),
        broker_orders_count=len(broker_orders),
        issues=critical_issues,
        raw={
            "limit": limit,
            "non_critical_stale_ack_not_filled": len(non_critical_issues),
        },
    )

    print("ORDER_ACK_RECONCILIATION")
    print(
        f"acks={len(acks)} broker_orders={len(broker_orders)} "
        f"issues={len(critical_issues)} "
        f"non_critical_stale_ack_not_filled={len(non_critical_issues)} "
        f"broker_snapshots_saved={broker_snapshots_saved}"
    )
    print(f"run_id={run_id}")

    for issue in non_critical_issues:
        print(
            f"ORDER_ACK_RECON_WARNING type=STALE_ACK_NOT_FILLED "
            f"order_id={issue.order_id} symbol={issue.symbol} "
            f"reason=ack_missing_at_broker_but_not_filled_and_old"
        )

    for issue in critical_issues:
        print(
            f"ORDER_ACK_RECON_ISSUE type={issue.issue_type} "
            f"order_id={issue.order_id} symbol={issue.symbol} reason={issue.reason}"
        )

    return 1 if critical_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
