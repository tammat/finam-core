from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import os
import psycopg2


@dataclass(frozen=True, slots=True)
class BrLongShadowEventV1:
    symbol: str
    side: str
    strategy: str
    signal_id: str | None
    price: Decimal | None
    quantity: Decimal | None
    mode: str
    allowed: bool
    shadow_logged: bool
    reason: str
    created_at: datetime | None = None


class BrLongShadowAccumulatorV1:
    """
    Накопитель shadow-событий BR LONG.

    Не отправляет заявки.
    Не меняет pipeline.
    Только пишет исследовательские события в PostgreSQL.
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not set")

    def ensure_schema(self) -> None:
        ddl = """
        create table if not exists research_br_long_shadow_signals (
            id bigserial primary key,
            created_at timestamptz not null default now(),
            symbol text not null,
            side text not null,
            strategy text not null,
            signal_id text,
            price numeric,
            quantity numeric,
            mode text not null,
            allowed boolean not null,
            shadow_logged boolean not null,
            reason text not null,
            source text not null default 'br_long_shadow_accumulation_v1'
        );

        create index if not exists idx_research_br_long_shadow_created_at
            on research_br_long_shadow_signals(created_at);

        create index if not exists idx_research_br_long_shadow_symbol
            on research_br_long_shadow_signals(symbol);

        create index if not exists idx_research_br_long_shadow_signal_id
            on research_br_long_shadow_signals(signal_id);
        """

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)

    def record(self, event: BrLongShadowEventV1) -> None:
        self.ensure_schema()

        created_at = event.created_at or datetime.now(timezone.utc)

        sql = """
        insert into research_br_long_shadow_signals (
            created_at,
            symbol,
            side,
            strategy,
            signal_id,
            price,
            quantity,
            mode,
            allowed,
            shadow_logged,
            reason
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
        """

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        created_at,
                        event.symbol,
                        event.side,
                        event.strategy,
                        event.signal_id,
                        event.price,
                        event.quantity,
                        event.mode,
                        event.allowed,
                        event.shadow_logged,
                        event.reason,
                    ),
                )
