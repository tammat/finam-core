#!/usr/bin/env python3
from __future__ import annotations

import os

import psycopg2

from finam_core.strategy.signal_strategy_attribution_gate_v1 import SignalStrategyAttributionGateV1
from finam_core.strategy.signal_strategy_discovery_repository_v1 import (
    SignalStrategyDiscoveryRepositoryV1,
    build_unresolved_signal_notification_v1,
    decision_to_payload_v1,
)


def main() -> int:
    dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

    print("=== SIGNAL STRATEGY UNRESOLVED NOTIFY REQUIRED V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    symbol = "UNKNOWN@RTSX"
    payload = {
        "reason": "new_pattern_unknown_market_structure",
        "timeframe": "M5",
        "price": 123.45,
        "features": {
            "atr_pct": 0.0042,
            "impulse": True,
            "compression_breakout": True,
        },
    }

    gate = SignalStrategyAttributionGateV1()
    decision = gate.resolve(symbol=symbol, payload=payload)

    print(
        "ATTRIBUTION_DECISION "
        f"allowed={int(decision.allowed)} "
        f"strategy={decision.strategy} "
        f"timeframe={decision.timeframe} "
        f"continuous_symbol={decision.continuous_symbol} "
        f"reason={decision.reason} "
        f"source={decision.source} "
        f"discovery_required={int(decision.discovery_required)}"
    )

    if decision.allowed:
        raise SystemExit("FAIL: unknown signal unexpectedly attributed")

    if not decision.discovery_required:
        raise SystemExit("FAIL: discovery_required must be true for unresolved signal")

    enriched_payload = decision_to_payload_v1(decision, payload)

    with psycopg2.connect(dsn) as conn:
        repo = SignalStrategyDiscoveryRepositoryV1(conn)

        event_id = repo.record_unresolved_signal(
            symbol=symbol,
            reason=decision.reason,
            source=decision.source,
            payload=enriched_payload,
            proposed_strategy=None,
            proposed_timeframe=decision.timeframe,
            proposed_continuous_symbol=decision.continuous_symbol,
        )
        # SIGNAL_STRATEGY_UNRESOLVED_TEST_ISOLATION_V1
        # Русский комментарий:
        # Diagnostic test не должен оставлять production NEW-события.
        # Сразу переводим тестовый discovery event в TEST_CLOSED.
        with conn.cursor() as cur:
            cur.execute(
                """
                update signal_strategy_discovery_events
                set
                    status = 'TEST_CLOSED',
                    analyst_comment = 'Тестовое событие unresolved strategy attribution gate; не рыночный инструмент.'
                where id = %s;
                """,
                (event_id,),
            )

        conn.commit()

    notification = build_unresolved_signal_notification_v1(
        event_id=event_id,
        symbol=symbol,
        decision=decision,
        payload=payload,
    )

    print(notification)

    if "SIGNAL_STRATEGY_UNRESOLVED_NOTIFY_REQUIRED" not in notification:
        raise SystemExit("FAIL: notification marker missing")

    print(f"discovery_event_id={event_id}")
    print("SIGNAL_STRATEGY_UNRESOLVED_NOTIFY_REQUIRED_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
