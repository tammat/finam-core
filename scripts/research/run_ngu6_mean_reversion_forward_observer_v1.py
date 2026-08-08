#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.ngu6_mean_reversion_forward_observer_v1 import (
    CANDIDATE_CODE,
    FORWARD_BOUNDARY,
    FREEZE_COMMIT,
    FREEZE_SHA256,
    SOURCE_VERSION,
    SYMBOL,
    TIMEFRAME,
    Bar,
    ContractSpecSnapshot,
    ForwardObserverContractError,
    build_forward_observations,
)


TABLE = "analytics.ngu6_mr_forward_observation_v1"

DDL = """
CREATE TABLE IF NOT EXISTS analytics.ngu6_mr_forward_observation_v1 (
    id bigserial PRIMARY KEY,

    candidate_code text NOT NULL,
    freeze_commit text NOT NULL,
    freeze_sha256 text NOT NULL,

    symbol text NOT NULL,
    timeframe text NOT NULL,

    signal_ts timestamptz NOT NULL,
    side text NOT NULL,

    market_entry_price numeric NOT NULL,
    entry_price numeric NOT NULL,

    exit_ts timestamptz,
    market_exit_price numeric,
    exit_price numeric,

    gross_pnl numeric,
    commission numeric,
    slippage numeric,
    net_pnl numeric,

    ac100 numeric,

    contract_spec_id bigint NOT NULL,
    contract_spec_valid_from timestamptz NOT NULL,
    contract_spec_valid_to timestamptz,
    contract_tick_size numeric NOT NULL,
    contract_tick_value numeric NOT NULL,
    contract_multiplier numeric NOT NULL,
    contract_spec_source_version text NOT NULL,

    observation_status text NOT NULL,

    shadow_only boolean NOT NULL DEFAULT true,
    broker_order_sent boolean NOT NULL DEFAULT false,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,

    source_version text NOT NULL,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    UNIQUE(candidate_code, signal_ts),

    CHECK (shadow_only),
    CHECK (NOT broker_order_sent),
    CHECK (NOT runtime_allowed),
    CHECK (NOT execution_enabled),

    CHECK (observation_status IN ('OPEN', 'CLOSED'))
);

CREATE INDEX IF NOT EXISTS
    idx_ngu6_mr_forward_observation_v1_status_ts
ON analytics.ngu6_mr_forward_observation_v1
    (observation_status, signal_ts);
"""


def load_bars(
    cursor: RealDictCursor,
) -> list[Bar]:
    cursor.execute(
        """
        SELECT ts, open, high, low, close, volume
        FROM public.market_bars
        WHERE symbol = %s
          AND timeframe = %s
        ORDER BY ts
        """,
        (SYMBOL, TIMEFRAME),
    )

    return [
        Bar(
            ts=row["ts"],
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
            volume=Decimal(str(row["volume"] or 0)),
        )
        for row in cursor.fetchall()
    ]


def load_contract_spec_at(
    cursor: RealDictCursor,
    signal_ts: datetime,
) -> ContractSpecSnapshot:
    cursor.execute(
        """
        SELECT
            id,
            valid_from,
            valid_to,
            tick_size,
            tick_value,
            contract_multiplier,
            source_version
        FROM analytics.market_contract_spec_v1
        WHERE symbol = %s
          AND valid_from <= %s
          AND (
                valid_to IS NULL
                OR %s < valid_to
          )
        ORDER BY valid_from DESC
        LIMIT 2
        """,
        (
            SYMBOL,
            signal_ts,
            signal_ts,
        ),
    )

    rows = cursor.fetchall()

    if len(rows) != 1:
        raise ForwardObserverContractError(
            "contract_spec_interval_resolution_failed:"
            f"{signal_ts.isoformat()}:count={len(rows)}"
        )

    row = rows[0]

    multiplier = Decimal(
        str(row["contract_multiplier"])
    )

    if multiplier <= 0:
        raise ForwardObserverContractError(
            "contract_multiplier_not_positive:"
            f"{signal_ts.isoformat()}"
        )

    return ContractSpecSnapshot(
        contract_spec_id=int(row["id"]),
        valid_from=row["valid_from"],
        valid_to=row["valid_to"],
        tick_size=Decimal(str(row["tick_size"])),
        tick_value=Decimal(str(row["tick_value"])),
        contract_multiplier=multiplier,
        source_version=str(row["source_version"]),
    )


def build_spec_map(
    cursor: RealDictCursor,
    bars: list[Bar],
) -> dict[datetime, ContractSpecSnapshot]:
    result = {}

    for bar in bars:
        if bar.ts <= FORWARD_BOUNDARY:
            continue

        result[bar.ts] = load_contract_spec_at(
            cursor,
            bar.ts,
        )

    return result


def upsert_observation(
    cursor: RealDictCursor,
    observation,
) -> tuple[bool, bool]:
    cursor.execute(
        f"""
        SELECT observation_status
        FROM {TABLE}
        WHERE candidate_code = %s
          AND signal_ts = %s
        FOR UPDATE
        """,
        (
            observation.candidate_code,
            observation.signal_ts,
        ),
    )

    existing = cursor.fetchone()

    if existing is not None:
        old_status = str(
            existing["observation_status"]
        )

        if old_status == "CLOSED":
            # CLOSED является immutable.
            return False, False

        if old_status != "OPEN":
            raise ForwardObserverContractError(
                f"unexpected_existing_status:{old_status}"
            )

        if observation.status != "CLOSED":
            return False, False

    cursor.execute(
        f"""
        INSERT INTO {TABLE} (
            candidate_code,
            freeze_commit,
            freeze_sha256,
            symbol,
            timeframe,
            signal_ts,
            side,
            market_entry_price,
            entry_price,
            exit_ts,
            market_exit_price,
            exit_price,
            gross_pnl,
            commission,
            slippage,
            net_pnl,
            ac100,
            contract_spec_id,
            contract_spec_valid_from,
            contract_spec_valid_to,
            contract_tick_size,
            contract_tick_value,
            contract_multiplier,
            contract_spec_source_version,
            observation_status,
            shadow_only,
            broker_order_sent,
            runtime_allowed,
            execution_enabled,
            source_version
        )
        VALUES (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            true,false,false,false,%s
        )
        ON CONFLICT (candidate_code, signal_ts)
        DO UPDATE SET
            exit_ts = EXCLUDED.exit_ts,
            market_exit_price = EXCLUDED.market_exit_price,
            exit_price = EXCLUDED.exit_price,
            gross_pnl = EXCLUDED.gross_pnl,
            commission = EXCLUDED.commission,
            slippage = EXCLUDED.slippage,
            net_pnl = EXCLUDED.net_pnl,
            observation_status = EXCLUDED.observation_status,
            shadow_only = true,
            broker_order_sent = false,
            runtime_allowed = false,
            execution_enabled = false,
            updated_at = now()
        """,
        (
            observation.candidate_code,
            FREEZE_COMMIT,
            FREEZE_SHA256,
            SYMBOL,
            TIMEFRAME,
            observation.signal_ts,
            observation.side,
            observation.market_entry_price,
            observation.entry_price,
            observation.exit_ts,
            observation.market_exit_price,
            observation.exit_price,
            observation.gross_pnl,
            observation.commission,
            observation.slippage,
            observation.net_pnl,
            observation.ac100,
            observation.contract_spec.contract_spec_id,
            observation.contract_spec.valid_from,
            observation.contract_spec.valid_to,
            observation.contract_spec.tick_size,
            observation.contract_spec.tick_value,
            observation.contract_spec.contract_multiplier,
            observation.contract_spec.source_version,
            observation.status,
            SOURCE_VERSION,
        ),
    )

    return (
        existing is None,
        existing is not None,
    )


def main() -> int:
    inserted = 0
    updated = 0

    with psycopg2.connect(build_psycopg_url()) as conn:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(DDL)

            bars = load_bars(cursor)

            forward_bar_count = sum(
                bar.ts > FORWARD_BOUNDARY
                for bar in bars
            )

            if forward_bar_count == 0:
                cursor.execute(
                    f"""
                    SELECT
                        count(*)::bigint AS total,
                        count(*) FILTER (
                            WHERE observation_status='OPEN'
                        )::bigint AS open_count,
                        count(*) FILTER (
                            WHERE observation_status='CLOSED'
                        )::bigint AS closed_count,
                        count(*) FILTER (
                            WHERE broker_order_sent
                               OR runtime_allowed
                               OR execution_enabled
                               OR NOT shadow_only
                        )::bigint AS unsafe_count
                    FROM {TABLE}
                    WHERE candidate_code = %s
                    """,
                    (CANDIDATE_CODE,),
                )

                summary = cursor.fetchone()

                print(
                    f"forward_bar_count={forward_bar_count}"
                )
                print("generated_observations=0")
                print("inserted=0")
                print("updated=0")
                print(f"total={summary['total']}")
                print(f"open={summary['open_count']}")
                print(f"closed={summary['closed_count']}")
                print(f"unsafe={summary['unsafe_count']}")
                print("broker_orders=0")
                print("runtime_allowed=0")
                print("execution_enabled=0")
                print(
                    "VERDICT="
                    "NGU6_FORWARD_OBSERVER_ZERO_DATA_OK"
                )

                return 0

            spec_map = build_spec_map(
                cursor,
                bars,
            )

            observations = build_forward_observations(
                bars,
                spec_map,
            )

            for observation in observations:
                was_inserted, was_updated = (
                    upsert_observation(
                        cursor,
                        observation,
                    )
                )

                inserted += int(was_inserted)
                updated += int(was_updated)

            cursor.execute(
                f"""
                SELECT
                    count(*)::bigint AS total,
                    count(*) FILTER (
                        WHERE observation_status='OPEN'
                    )::bigint AS open_count,
                    count(*) FILTER (
                        WHERE observation_status='CLOSED'
                    )::bigint AS closed_count,
                    count(*) FILTER (
                        WHERE broker_order_sent
                           OR runtime_allowed
                           OR execution_enabled
                           OR NOT shadow_only
                    )::bigint AS unsafe_count
                FROM {TABLE}
                WHERE candidate_code = %s
                """,
                (CANDIDATE_CODE,),
            )

            summary = cursor.fetchone()

    print(f"forward_bar_count={forward_bar_count}")
    print(
        f"generated_observations={len(observations)}"
    )
    print(f"inserted={inserted}")
    print(f"updated={updated}")
    print(f"total={summary['total']}")
    print(f"open={summary['open_count']}")
    print(f"closed={summary['closed_count']}")
    print(f"unsafe={summary['unsafe_count']}")
    print("broker_orders=0")
    print("runtime_allowed=0")
    print("execution_enabled=0")
    print("VERDICT=NGU6_FORWARD_OBSERVER_V1_OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
