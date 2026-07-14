#!/usr/bin/env python3
"""Backfill regime snapshots for relationship symbols from versioned policy."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from scripts.analytics.build_regime_snapshots_v2 import (
    _session_from_ts_msk,
    classify,
    load_intermarket_state,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "research" / "relationship_data_quality_v1.json"


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    symbols = sorted({str(item) for item in policy["symbols"] if str(item).endswith("@MISX")})
    database_url = os.environ.get("DATABASE_URL", "postgresql:///finam_core")
    with psycopg.connect(database_url) as connection:
        intermarket_state = load_intermarket_state(connection)
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT ts, symbol, timeframe, to_jsonb(f.*) AS payload,
                       EXTRACT(HOUR FROM (ts AT TIME ZONE 'Europe/Moscow'))::integer AS hour_msk
                FROM public.feature_snapshots f
                WHERE symbol = ANY(%s) AND timeframe = %s
                ORDER BY symbol, ts
                """,
                (symbols, policy["timeframe"]),
            )
            rows = cursor.fetchall()
            values = []
            for row in rows:
                payload = dict(row["payload"] or {})
                regime, volatility, trend, compression, confidence = classify(payload)
                values.append(
                    (
                        row["ts"], row["symbol"], row["timeframe"], regime,
                        volatility, trend, compression, intermarket_state,
                        _session_from_ts_msk(int(row["hour_msk"] or 0)),
                        confidence, "feature_snapshots", Jsonb(payload),
                    )
                )
            cursor.executemany(
                """
                INSERT INTO public.analytics_regime_snapshots_v2 (
                    ts, trade_date, symbol, timeframe, regime, volatility_regime,
                    trend_regime, compression_state, intermarket_state, session_type,
                    confidence, source, payload
                ) VALUES (
                    %s, (%s AT TIME ZONE 'Europe/Moscow')::date, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (ts, symbol, timeframe, source) DO UPDATE SET
                    regime=excluded.regime, volatility_regime=excluded.volatility_regime,
                    trend_regime=excluded.trend_regime,
                    compression_state=excluded.compression_state,
                    intermarket_state=excluded.intermarket_state,
                    session_type=excluded.session_type, confidence=excluded.confidence,
                    payload=excluded.payload, updated_at=now()
                """,
                [
                    (ts, ts, symbol, timeframe, regime, volatility, trend, compression,
                     intermarket, session, confidence, source, payload)
                    for ts, symbol, timeframe, regime, volatility, trend, compression,
                        intermarket, session, confidence, source, payload in values
                ],
            )
        connection.commit()
    print(
        f"RELATIONSHIP_REGIME_BACKFILL_OK rows={len(values)} "
        f"policy={policy['contract_version']}"
    )


if __name__ == "__main__":
    main()
