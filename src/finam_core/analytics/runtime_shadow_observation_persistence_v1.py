from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class RuntimeShadowPersistenceRowV1:
    symbol: str
    side: str
    hour_msk: int
    expectancy_points: float
    pnl_points: float
    closed_trades: int
    decay_state: str
    shadow_block_candidate: bool


class RuntimeShadowObservationPersistenceV1:
    """
    Русский комментарий:
    Слой сохранения shadow-наблюдений runtime governance в PostgreSQL.
    Ничего не блокирует, только пишет наблюдения.
    """

    CREATE_SQL = """
    CREATE TABLE IF NOT EXISTS runtime_shadow_observation_v1 (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        hour_msk INTEGER NOT NULL,
        expectancy_points DOUBLE PRECISION NOT NULL,
        pnl_points DOUBLE PRECISION NOT NULL,
        closed_trades INTEGER NOT NULL,
        decay_state TEXT NOT NULL,
        shadow_block_candidate BOOLEAN NOT NULL,
        raw_json JSONB NOT NULL DEFAULT '{}'::jsonb
    );
    """

    INSERT_SQL = """
    INSERT INTO runtime_shadow_observation_v1 (
        created_at,
        symbol,
        side,
        hour_msk,
        expectancy_points,
        pnl_points,
        closed_trades,
        decay_state,
        shadow_block_candidate,
        raw_json
    )
    VALUES (
        %(created_at)s,
        %(symbol)s,
        %(side)s,
        %(hour_msk)s,
        %(expectancy_points)s,
        %(pnl_points)s,
        %(closed_trades)s,
        %(decay_state)s,
        %(shadow_block_candidate)s,
        %(raw_json)s::jsonb
    );
    """

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or build_psycopg_url()

    def ensure_table(self) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(self.CREATE_SQL)
            conn.commit()

    def persist(self, row: RuntimeShadowPersistenceRowV1) -> None:
        params = {
            "created_at": datetime.now(timezone.utc),
            "symbol": row.symbol,
            "side": row.side,
            "hour_msk": int(row.hour_msk),
            "expectancy_points": float(row.expectancy_points),
            "pnl_points": float(row.pnl_points),
            "closed_trades": int(row.closed_trades),
            "decay_state": row.decay_state,
            "shadow_block_candidate": bool(row.shadow_block_candidate),
            "raw_json": json.dumps(
                {
                    "source": "runtime_shadow_observation_persistence_v1",
                    "shadow_only": True,
                },
                ensure_ascii=False,
            ),
        }

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(self.INSERT_SQL, params)
            conn.commit()
