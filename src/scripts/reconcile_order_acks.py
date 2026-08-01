# -*- coding: utf-8 -*-
"""
CLI: сверка order_acks из PostgreSQL с текущими заявками брокера Finam.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import grpc
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
BACKOFF_FILE = Path(os.getenv("ORDER_ACK_BACKOFF_FILE", "/tmp/finam-order-ack-reconcile.backoff"))


def _defer_reason() -> str | None:
    now = datetime.now(ZoneInfo("Europe/Moscow"))
    if now.weekday() >= 5:
        return "market_weekend"
    try:
        if float(BACKOFF_FILE.read_text(encoding="ascii")) > time.time():
            return "broker_backoff_active"
    except (FileNotFoundError, ValueError, OSError):
        pass
    return None


def _set_backoff() -> None:
    seconds = max(60, int(os.getenv("ORDER_ACK_UNAVAILABLE_BACKOFF_SECONDS", "300")))
    try:
        descriptor = os.open(BACKOFF_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii") as target:
            target.write(str(time.time() + seconds))
    except OSError:
        pass


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


def _ack_age_hours(ack) -> float:
    ts = getattr(ack, "ts", None)
    if ts is None:
        return 0.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 3600.0)


def _is_stale_not_filled_ack(ack) -> bool:
    # Русский комментарий:
    # Старый ACK со статусом принятой заявки, отсутствующей у брокера,
    # переводим в warning. Свежие ACK младше 24 часов не подавляем.
    if ack is None:
        return False

    if _ack_age_hours(ack) < 24.0:
        return False

    status = str(getattr(ack, "status", "") or "")
    raw = str(getattr(ack, "raw", "") or "")

    accepted = status == "1" or "ORDER_STATUS_NEW" in raw
    not_filled = (
        "executed_quantity" in raw and 'value: "0.0"' in raw
    ) or (
        "remaining_quantity" in raw and 'value: "1.0"' in raw
    )

    # Русский комментарий:
    # Для старых ACK status=1 достаточно статуса accepted.
    # Это не активная авария, если брокер уже не возвращает заявку.
    return accepted or not_filled


def _is_ack_missing_issue(issue) -> bool:
    return str(getattr(issue, "issue_type", "")) == "ACK_MISSING_AT_BROKER"


def main() -> int:
    deferred = _defer_reason()
    if deferred:
        print("ORDER_ACK_RECONCILIATION_DEFERRED")
        print(f"reason={deferred}")
        return 0
    limit = int(os.getenv("ORDER_ACK_RECONCILE_LIMIT", "100"))
    acks = OrderAckRepository().list_recent(limit=limit)

    client = FinamOrdersClient()
    try:
        broker_orders = [_broker_order_to_state(o) for o in client.get_orders()]
    except grpc.RpcError as exc:
        # Temporary broker/network outages are not reconciliation failures:
        # there is no trustworthy broker snapshot to compare with.  Defer the
        # run and let the timer retry instead of creating a systemd failure
        # storm or, worse, treating an empty response as missing orders.
        if exc.code() in {grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED}:
            _set_backoff()
            print("ORDER_ACK_RECONCILIATION_DEFERRED")
            print(f"broker_status={exc.code().name} reason=broker_snapshot_unavailable")
            return 0
        raise
    broker_snapshots_saved = BrokerOrderSnapshotStore().save_many(broker_orders)

    service = BrokerOrderReconciliationService(broker_orders)
    issues = []
    for ack in acks:
        issues.extend(service.check_ack(ack))

    # Русский комментарий:
    # ACK_MISSING_AT_BROKER означает, что старая ACK-запись не найдена
    # в текущем срезе брокерских заявок. Для systemd это warning, а не failure.
    critical_issues = []
    warning_issues = []

    for issue in issues:
        if str(getattr(issue, "issue_type", "")) == "ACK_MISSING_AT_BROKER":
            warning_issues.append(issue)
        else:
            critical_issues.append(issue)

    run_id = OrderReconciliationLogger().log_run(
        acks_count=len(acks),
        broker_orders_count=len(broker_orders),
        issues=critical_issues,
        raw={
            "limit": limit,
            "warning_ack_missing_at_broker": len(warning_issues),
        },
    )

    print("ORDER_ACK_RECONCILIATION")
    print(
        f"acks={len(acks)} broker_orders={len(broker_orders)} "
        f"issues={len(critical_issues)} "
        f"warnings={len(warning_issues)} "
        f"broker_snapshots_saved={broker_snapshots_saved}"
    )
    print(f"run_id={run_id}")

    for issue in warning_issues:
        print(
            f"ORDER_ACK_RECON_WARNING type=ACK_MISSING_AT_BROKER "
            f"order_id={issue.order_id} symbol={issue.symbol} reason={issue.reason}"
        )

    for issue in critical_issues:
        print(
            f"ORDER_ACK_RECON_ISSUE type={issue.issue_type} "
            f"order_id={issue.order_id} symbol={issue.symbol} reason={issue.reason}"
        )

    return 1 if critical_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
