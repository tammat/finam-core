from __future__ import annotations

import os
from typing import Optional

import psycopg2


DDL = """
create table if not exists research_regime_guard_shadow (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    signal_id text,
    strategy text,

    regime_key text not null,
    classification text not null,

    would_block boolean not null,
    actual_block boolean not null default false,
    advisory_only boolean not null default true,

    reason text,
    source text not null default 'regime_guard_shadow_accumulation_v1'
);

create index if not exists idx_regime_guard_shadow_created_at
    on research_regime_guard_shadow(created_at desc);

create index if not exists idx_regime_guard_shadow_regime_key
    on research_regime_guard_shadow(regime_key);

create index if not exists idx_regime_guard_shadow_symbol
    on research_regime_guard_shadow(symbol);
"""


class RegimeGuardShadowAccumulator:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    def ensure_schema(self) -> None:
        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(DDL)

    def record(
        self,
        *,
        symbol: str,
        signal_id: Optional[str],
        strategy: Optional[str],
        regime_key: str,
        classification: str,
        would_block: bool,
        reason: Optional[str],
    ) -> None:
        self.ensure_schema()

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into research_regime_guard_shadow (
                        symbol,
                        signal_id,
                        strategy,
                        regime_key,
                        classification,
                        would_block,
                        actual_block,
                        advisory_only,
                        reason,
                        source
                    )
                    values (%s,%s,%s,%s,%s,%s,false,true,%s,'regime_guard_shadow_accumulation_v1')
                    """,
                    (
                        symbol,
                        signal_id,
                        strategy,
                        regime_key,
                        classification,
                        bool(would_block),
                        reason,
                    ),
                )
