from __future__ import annotations

import os

from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.execution.client_order_id_factory import build_client_order_id


def main() -> int:
    if os.getenv("PROTECTIVE_REAL_SEND_PROBE_ARMED", "0") != "1":
        print("PROTECTIVE_STOP_REAL_SEND_PROBE_DISABLED")
        return 0

    symbol = os.getenv("PROTECTIVE_SYMBOL", "SBER@MISX").strip().upper()
    qty = float(os.getenv("PROTECTIVE_PROBE_QTY", "1"))
    stop_price = float(os.getenv("PROTECTIVE_PROBE_STOP_PRICE", "0"))

    if qty <= 0 or stop_price <= 0:
        print(f"PROTECTIVE_STOP_REAL_SEND_PROBE_INVALID_INPUT qty={qty} stop={stop_price}")
        return 0

    client_order_id = build_client_order_id(
        strategy="protective_probe",
        symbol=symbol,
        side="SELL",
    )

    print(
        f"PROTECTIVE_STOP_REAL_SEND_PROBE_BEGIN "
        f"symbol={symbol} qty={qty} stop={stop_price} client_order_id={client_order_id}",
        flush=True,
    )

    response = FinamOrdersClient().place_stop_order(
        symbol=symbol,
        side="SELL",
        qty=qty,
        stop_price=stop_price,
        client_order_id=client_order_id,
    )

    broker_order_id = str(
        response.get("transaction_id")
        or response.get("order_id")
        or response.get("stop_id")
        or ""
    )

    print(
        f"PROTECTIVE_STOP_REAL_SEND_PROBE_RESULT "
        f"broker_order_id={broker_order_id} response={response}",
        flush=True,
    )

    if broker_order_id.startswith("dry_stop_"):
        print("PROTECTIVE_STOP_REAL_SEND_PROBE_DRY_RESULT")
        return 2

    if not broker_order_id:
        print("PROTECTIVE_STOP_REAL_SEND_PROBE_EMPTY_ORDER_ID")
        return 3

    print("PROTECTIVE_STOP_REAL_SEND_PROBE_REAL_ACK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
