#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST WIRE SIGNAL STRATEGY ATTRIBUTION GATE TO STORAGE WRITER V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/finam_core/storage/postgres_logger.py \
  src/finam_core/strategy/signal_strategy_attribution_gate_v1.py \
  src/finam_core/strategy/signal_strategy_discovery_repository_v1.py

grep -q "WIRE_SIGNAL_STRATEGY_ATTRIBUTION_GATE_TO_STORAGE_WRITER_V1" \
  src/finam_core/storage/postgres_logger.py

grep -q "SignalStrategyAttributionGateV1" \
  src/finam_core/storage/postgres_logger.py

grep -q "signal_strategy_discovery_events" \
  src/finam_core/strategy/signal_strategy_discovery_repository_v1.py

PYTHONPATH=src python3 - <<'PY' | tee /tmp/wire_signal_strategy_attribution_gate_to_storage_writer_v1.log
from __future__ import annotations

import os
import inspect
import psycopg2

from finam_core.storage.postgres_logger import PostgresLogger


dsn = os.getenv("DATABASE_URL", "dbname=finam_core user=postgres")

print("=== STORAGE WRITER ATTRIBUTION GATE RUNTIME CHECK ===")
print(f"POSTGRES_LOGGER_INIT={inspect.signature(PostgresLogger.__init__)}")


def build_logger(conn):
    """
    Русский комментарий:
    PostgresLogger в разных версиях проекта мог принимать разные параметры.
    Тест не должен ломаться из-за имени аргумента конструктора.
    """
    attempts = [
        lambda: PostgresLogger(conn, enabled=True),
        lambda: PostgresLogger(conn),
        lambda: PostgresLogger(connection=conn, enabled=True),
        lambda: PostgresLogger(connection=conn),
        lambda: PostgresLogger(db=conn, enabled=True),
        lambda: PostgresLogger(db=conn),
        lambda: PostgresLogger(enabled=True),
        lambda: PostgresLogger(),
    ]

    last_error = None

    for factory in attempts:
        try:
            logger = factory()

            if getattr(logger, "conn", None) is None:
                try:
                    setattr(logger, "conn", conn)
                except Exception:
                    pass

            if hasattr(logger, "enabled"):
                try:
                    setattr(logger, "enabled", True)
                except Exception:
                    pass

            if getattr(logger, "conn", None) is not None:
                return logger
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"cannot build PostgresLogger: {last_error}")


with psycopg2.connect(dsn) as conn:
    logger = build_logger(conn)

    good_fill_id = "test_attr_gate_good_br_001"
    bad_fill_id = "test_attr_gate_bad_unknown_001"

    with conn.cursor() as cur:
        cur.execute("delete from trades where fill_id in (%s, %s)", (good_fill_id, bad_fill_id))
        cur.execute("delete from fills where fill_id in (%s, %s)", (good_fill_id, bad_fill_id))
        cur.execute(
            """
            update signal_strategy_discovery_events
            set status = 'TEST_CLOSED',
                analyst_comment = 'cleanup before storage writer attribution gate test'
            where payload->>'test_case' in ('storage_writer_attr_gate_unknown');
            """
        )
        conn.commit()

    logger.log_fill(
        symbol="BRN6@RTSX",
        side="BUY",
        qty=1,
        price=80.0,
        trade_id=good_fill_id,
        execution_type="paper",
        commission=0.01,
        payload={
            "test_case": "storage_writer_attr_gate_good",
            "reason": "BR_M5_BREAKOUT_UP_trend_high_vol",
            "timeframe": "M5",
            "paper_only": True,
            "execution_type": "paper",
        },
    )
    conn.commit()

    with conn.cursor() as cur:
        cur.execute(
            """
            select
                symbol,
                strategy,
                timeframe,
                continuous_symbol
            from trades
            where fill_id = %s;
            """,
            (good_fill_id,),
        )
        row = cur.fetchone()

    if row is None:
        raise SystemExit("FAIL: attributed trade was not inserted")

    print(
        "GOOD_TRADE_ROW "
        f"symbol={row[0]} "
        f"strategy={row[1]} "
        f"timeframe={row[2]} "
        f"continuous_symbol={row[3]}"
    )

    if row[1] != "BR_CONSERVATIVE_BREAKOUT":
        raise SystemExit("FAIL: strategy attribution mismatch")

    if row[2] != "M5":
        raise SystemExit("FAIL: timeframe attribution mismatch")

    if row[3] != "BR_CONT":
        raise SystemExit("FAIL: continuous symbol attribution mismatch")

    logger.log_fill(
        symbol="UNKNOWN@RTSX",
        side="BUY",
        qty=1,
        price=1.0,
        trade_id=bad_fill_id,
        execution_type="paper",
        commission=0.0,
        payload={
            "test_case": "storage_writer_attr_gate_unknown",
            "reason": "new_pattern_unknown_market_structure",
            "timeframe": "M5",
            "paper_only": True,
            "execution_type": "paper",
        },
    )
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("select count(*) from trades where fill_id = %s", (bad_fill_id,))
        bad_trade_count = cur.fetchone()[0]

        cur.execute(
            """
            select count(*)
            from signal_strategy_discovery_events
            where symbol = 'UNKNOWN@RTSX'
              and reason = 'SIGNAL_STRATEGY_UNRESOLVED'
              and payload->>'test_case' = 'storage_writer_attr_gate_unknown'
              and status = 'NEW';
            """
        )
        discovery_count = cur.fetchone()[0]

    print(f"BAD_TRADE_COUNT={bad_trade_count}")
    print(f"DISCOVERY_NEW_COUNT={discovery_count}")

    if bad_trade_count != 0:
        raise SystemExit("FAIL: unresolved signal produced normal trade")

    if discovery_count < 1:
        raise SystemExit("FAIL: unresolved signal discovery event was not created")

    with conn.cursor() as cur:
        cur.execute(
            """
            update signal_strategy_discovery_events
            set status = 'TEST_CLOSED',
                analyst_comment = 'storage writer attribution gate test event closed'
            where symbol = 'UNKNOWN@RTSX'
              and payload->>'test_case' = 'storage_writer_attr_gate_unknown'
              and status = 'NEW';
            """
        )
        cur.execute("delete from trades where fill_id = %s", (good_fill_id,))
        cur.execute("delete from fills where fill_id in (%s, %s)", (good_fill_id, bad_fill_id))
        conn.commit()

print("WIRE_SIGNAL_STRATEGY_ATTRIBUTION_GATE_TO_STORAGE_WRITER_V1_OK")
PY
grep -q "GOOD_TRADE_ROW" /tmp/wire_signal_strategy_attribution_gate_to_storage_writer_v1.log
grep -q "strategy=BR_CONSERVATIVE_BREAKOUT" /tmp/wire_signal_strategy_attribution_gate_to_storage_writer_v1.log
grep -q "BAD_TRADE_COUNT=0" /tmp/wire_signal_strategy_attribution_gate_to_storage_writer_v1.log
grep -q "DISCOVERY_NEW_COUNT=" /tmp/wire_signal_strategy_attribution_gate_to_storage_writer_v1.log
grep -q "WIRE_SIGNAL_STRATEGY_ATTRIBUTION_GATE_TO_STORAGE_WRITER_V1_OK" /tmp/wire_signal_strategy_attribution_gate_to_storage_writer_v1.log
grep -q "SIGNAL_STRATEGY_UNRESOLVED_NOTIFY_REQUIRED" /tmp/wire_signal_strategy_attribution_gate_to_storage_writer_v1.log

sudo -u postgres psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
\pset pager off

select
    'ATTR_GATE_TEST_CLEANUP_OK' as check_name,
    count(*) filter (where fill_id in ('test_attr_gate_good_br_001', 'test_attr_gate_bad_unknown_001')) as leftover_test_trades
from trades;

select
    'UNKNOWN_TEST_EVENTS_STATUS' as check_name,
    count(*) filter (where status = 'NEW') as new_unknown_test_events,
    count(*) filter (where status = 'TEST_CLOSED') as test_closed_unknown_test_events
from signal_strategy_discovery_events
where symbol = 'UNKNOWN@RTSX'
  and payload->>'test_case' = 'storage_writer_attr_gate_unknown';
SQL

echo TEST_WIRE_SIGNAL_STRATEGY_ATTRIBUTION_GATE_TO_STORAGE_WRITER_V1_OK
