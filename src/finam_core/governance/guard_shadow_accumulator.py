from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import os
import psycopg2


DDL = """
create table if not exists guard_shadow_accumulation (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    side text not null,
    session_bucket text not null,

    classification text not null,
    reason text not null,

    would_block boolean not null default false,
    actual_block boolean not null default false,
    advisory_only boolean not null default true,

    signal_id text,
    source text not null default 'guard_shadow_accumulation_v1',

    payload jsonb not null default '{}'::jsonb
);

create index if not exists idx_guard_shadow_accumulation_created
    on guard_shadow_accumulation(created_at desc);

create index if not exists idx_guard_shadow_accumulation_key
    on guard_shadow_accumulation(symbol, strategy, timeframe, side, session_bucket);

create index if not exists idx_guard_shadow_accumulation_classification
    on guard_shadow_accumulation(classification, would_block, actual_block);
"""


@dataclass(frozen=True, slots=True)
class GuardShadowEvent:
    symbol: str
    strategy: str
    timeframe: str
    side: str
    session_bucket: str
    classification: str
    reason: str
    would_block: bool
    actual_block: bool = False
    advisory_only: bool = True
    signal_id: Optional[str] = None


class GuardShadowAccumulator:
    def __init__(self, dsn: Optional[str] = None, source: str = "guard_shadow_accumulation_v1"):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        self.source = source
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    def ensure_schema(self) -> None:
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(DDL)

    def record(self, event: GuardShadowEvent) -> None:
        self.ensure_schema()

        sql = """
            insert into guard_shadow_accumulation (
                symbol,
                strategy,
                timeframe,
                side,
                session_bucket,
                classification,
                reason,
                would_block,
                actual_block,
                advisory_only,
                signal_id,
                source,
                payload
            )
            values (
                %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s,
                %s,
                jsonb_build_object(
                    'version', 'guard_shadow_accumulation_v1',
                    'runtime_mode', 'shadow',
                    'actual_block', %s,
                    'advisory_only', %s
                )
            )
        """

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        event.symbol,
                        event.strategy,
                        event.timeframe,
                        event.side,
                        event.session_bucket,
                        event.classification,
                        event.reason,
                        event.would_block,
                        event.actual_block,
                        event.advisory_only,
                        event.signal_id,
                        self.source,
                        event.actual_block,
                        event.advisory_only,
                    ),
                )
