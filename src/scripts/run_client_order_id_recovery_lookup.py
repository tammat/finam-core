from __future__ import annotations

import os
import psycopg2

from finam_core.adapters.grpc.orders_client import FinamOrdersClient
from finam_core.execution.finam_order_identity_extraction import (
    FinamOrderIdentityExtraction,
)
from finam_core.execution.real_order_state_synchronizer import (
    RealOrderStateSynchronizer,
)
from finam_core.execution.execution_intent_transition_service import (
    ExecutionIntentTransitionService,
)


def _order_client_order_id(order) -> str:
    order_obj = getattr(order, "order", None)

    if order_obj is not None:
        return str(getattr(order_obj, "client_order_id", "") or "")

    if isinstance(order, dict):
        nested = order.get("order") or {}
        if isinstance(nested, dict):
            return str(nested.get("client_order_id") or "")
        return str(order.get("client_order_id") or "")

    return ""


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    client = FinamOrdersClient()

    try:
        orders = client.get_orders()
    except Exception as exc:
        print(
            f"CLIENT_ORDER_ID_RECOVERY_BROKER_UNAVAILABLE error={type(exc).__name__}:{exc}",
            flush=True,
        )
        print("CLIENT_ORDER_ID_RECOVERY_LOOKUP_OK scanned=0 recovered=0 broker_unavailable=1", flush=True)
        return 0

    extractor = FinamOrderIdentityExtraction()
    synchronizer = RealOrderStateSynchronizer()
    transition_service = ExecutionIntentTransitionService()

    recovered = 0
    scanned = 0

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    id,
                    symbol,
                    side,
                    client_order_id
                from execution_intents
                where intent_state in ('SENDING','RECONCILE_REQUIRED')
                  and coalesce(client_order_id,'') <> ''
                  and coalesce(broker_order_id,'') = ''
                order by updated_at asc
                limit 20
            """)

            rows = cur.fetchall()

            for intent_id, symbol, side, client_order_id in rows:
                scanned += 1
                target = str(client_order_id)

                matched_order = None

                for order in orders:
                    if _order_client_order_id(order) == target:
                        matched_order = order
                        break

                if matched_order is None:
                    print(
                        "CLIENT_ORDER_ID_RECOVERY_NOT_FOUND "
                        f"intent_id={intent_id} symbol={symbol} client_order_id={target}",
                        flush=True,
                    )
                    continue

                identity = extractor.extract(matched_order)

                if not identity.broker_order_id:
                    print(
                        "CLIENT_ORDER_ID_RECOVERY_NO_BROKER_ORDER_ID "
                        f"intent_id={intent_id} symbol={symbol} client_order_id={target}",
                        flush=True,
                    )
                    continue

                decision = synchronizer.map_broker_status(
                    broker_status=identity.status or "UNKNOWN",
                )

                transition = transition_service.transition(
                    cur,
                    intent_id=int(intent_id),
                    next_state=decision.intent_state,
                    reason=f"client_order_id_recovery:{decision.reason}",
                )

                if not transition.applied:
                    print(
                        "CLIENT_ORDER_ID_RECOVERY_TRANSITION_BLOCKED "
                        f"intent_id={intent_id} from={transition.previous_state} "
                        f"to={transition.next_state} reason={transition.reason}",
                        flush=True,
                    )
                    continue

                cur.execute("""
                    update execution_intents
                    set
                        broker_order_id = %s,
                        broker_exec_id = %s,
                        updated_at = now()
                    where id = %s
                """, (
                    identity.broker_order_id,
                    identity.broker_exec_id,
                    intent_id,
                ))

                recovered += 1

                print(
                    "CLIENT_ORDER_ID_RECOVERY_OK "
                    f"intent_id={intent_id} symbol={symbol} "
                    f"client_order_id={target} "
                    f"broker_order_id={identity.broker_order_id} "
                    f"broker_exec_id={identity.broker_exec_id} "
                    f"state={decision.intent_state}",
                    flush=True,
                )

    print(
        f"CLIENT_ORDER_ID_RECOVERY_LOOKUP_OK scanned={scanned} recovered={recovered}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
