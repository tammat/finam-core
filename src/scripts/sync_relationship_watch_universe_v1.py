#!/usr/bin/env python3
"""Synchronize ingestible relationship symbols into the market-data watch universe."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "research" / "relationship_data_quality_v1.json"


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    version = str(policy["contract_version"])
    symbols = sorted({str(item) for item in policy["symbols"] if str(item).endswith("@MISX")})
    database_url = os.environ.get("DATABASE_URL", "postgresql:///finam_core")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for symbol in symbols:
                cursor.execute(
                    """
                    INSERT INTO public.market_data_watch_universe
                        (symbol, asset_group, timeframe, is_enabled, reason, updated_at)
                    VALUES (%s, 'EQUITY', %s, true, %s, now())
                    ON CONFLICT (symbol) DO UPDATE SET
                        is_enabled = true,
                        reason = EXCLUDED.reason,
                        updated_at = now()
                    """,
                    (symbol, policy["timeframe"], f"versioned_relationship_policy:{version}"),
                )
        connection.commit()
    print(f"RELATIONSHIP_WATCH_UNIVERSE_SYNCED symbols={len(symbols)} policy={version}")


if __name__ == "__main__":
    main()
