import os
import psycopg2
from dotenv import load_dotenv

from core.event_bus import EventBus
from storage.postgres_event_store import PostgresEventStore
from core.events import StrategySignalEvent


load_dotenv()


def build_bus(dsn: str) -> EventBus:
    store = PostgresEventStore(dsn)
    return EventBus(event_store=store)


def count_events(dsn: str) -> int:
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events;")
            return cur.fetchone()[0]


def main():
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("POSTGRES_DSN not set")

    # очистка
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events;")
        conn.commit()

    bus = build_bus(dsn)

    # создаём событие (id генерируется внутри)
    event = StrategySignalEvent(
        symbol="NG",
        side="BUY",
        qty=1,
        price=100.0,
    )

    # публикуем дважды один и тот же объект
    bus.publish(event)
    bus.publish(event)

    total = count_events(dsn)

    print("Events in DB:", total)

    if total != 1:
        raise AssertionError("Idempotency failed")

    print("ok: idempotent append works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())