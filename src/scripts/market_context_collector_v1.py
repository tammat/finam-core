from __future__ import annotations

import json
from datetime import date

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MARKET_CONTEXT_COLLECTOR_V1"


def _table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists", (table_name,))
    row = cur.fetchone()
    return bool(row and row["exists"])


def _latest_regime(cur, symbol: str, timeframe: str) -> tuple[str, str]:
    if not _table_exists(cur, "public.analytics_regime_snapshots_v2"):
        return "UNKNOWN", "source_missing"

    cur.execute(
        """
        SELECT *
        FROM public.analytics_regime_snapshots_v2
        WHERE (%s IS NULL OR symbol = %s)
        ORDER BY created_at DESC NULLS LAST
        LIMIT 1
        """,
        (symbol, symbol),
    )
    row = cur.fetchone()
    if not row:
        return "UNKNOWN", "no_row"

    for key in ("regime_code", "regime", "market_regime", "state"):
        if key in row and row[key]:
            return str(row[key]).upper(), "analytics_regime_snapshots_v2"

    return "UNKNOWN", "no_regime_column"


def _feature_state(cur, symbol: str, timeframe: str) -> tuple[str, str, str]:
    if not _table_exists(cur, "public.feature_snapshots"):
        return "UNKNOWN", "UNKNOWN", "source_missing"

    cur.execute(
        """
        SELECT *
        FROM public.feature_snapshots
        WHERE (%s IS NULL OR symbol = %s)
        ORDER BY created_at DESC NULLS LAST
        LIMIT 1
        """,
        (symbol, symbol),
    )
    row = cur.fetchone()
    if not row:
        return "UNKNOWN", "UNKNOWN", "no_row"

    volatility = "UNKNOWN"
    liquidity = "UNKNOWN"

    for key in ("volatility_state", "vol_state", "atr_state"):
        if key in row and row[key]:
            volatility = str(row[key]).upper()
            break

    for key in ("liquidity_state", "liq_state", "volume_state"):
        if key in row and row[key]:
            liquidity = str(row[key]).upper()
            break

    return volatility, liquidity, "feature_snapshots"


def _snapshot_state(cur, symbol: str) -> tuple[str, str, str]:
    if not _table_exists(cur, "public.market_snapshot_v1"):
        return "UNKNOWN", "UNKNOWN", "source_missing"

    cur.execute(
        """
        SELECT *
        FROM public.market_snapshot_v1
        WHERE (%s IS NULL OR symbol = %s)
        ORDER BY created_at DESC NULLS LAST
        LIMIT 1
        """,
        (symbol, symbol),
    )
    row = cur.fetchone()
    if not row:
        return "UNKNOWN", "UNKNOWN", "no_row"

    volume_state = "UNKNOWN"
    spread_state = "UNKNOWN"

    for key in ("volume_state", "volume_quality", "volume_regime"):
        if key in row and row[key]:
            volume_state = str(row[key]).upper()
            break

    for key in ("spread_state", "spread_quality", "spread_regime"):
        if key in row and row[key]:
            spread_state = str(row[key]).upper()
            break

    return volume_state, spread_state, "market_snapshot_v1"


def _session_state(cur) -> tuple[str, str]:
    if not _table_exists(cur, "public.market_event_calendar"):
        return "UNKNOWN", "source_missing"

    cur.execute(
        """
        SELECT *
        FROM public.market_event_calendar
        ORDER BY created_at DESC NULLS LAST
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row:
        return "UNKNOWN", "no_row"

    for key in ("session_state", "event_type", "calendar_state"):
        if key in row and row[key]:
            return str(row[key]).upper(), "market_event_calendar"

    return "UNKNOWN", "no_session_column"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT symbol, timeframe
                FROM analytics.edge_score_model_v2
                WHERE symbol IS NOT NULL
                  AND timeframe IS NOT NULL
                ORDER BY symbol, timeframe
                """
            )
            targets = cur.fetchall()

            inserted = 0

            for target in targets:
                symbol = target["symbol"]
                timeframe = target["timeframe"]

                regime_code, regime_source = _latest_regime(cur, symbol, timeframe)
                volatility_state, liquidity_state, feature_source = _feature_state(cur, symbol, timeframe)
                volume_state, spread_state, snapshot_source = _snapshot_state(cur, symbol)
                session_state, calendar_source = _session_state(cur)

                evidence = {
                    "source_version": SOURCE_VERSION,
                    "regime_source": regime_source,
                    "feature_source": feature_source,
                    "snapshot_source": snapshot_source,
                    "calendar_source": calendar_source,
                    "collector_mode": "aggregate_existing_sources",
                    "no_new_edge_calculation": True,
                }

                cur.execute(
                    """
                    INSERT INTO knowledge.market_context_v1
                    (
                        symbol,
                        regime_code,
                        context_date,
                        timeframe,
                        volatility_state,
                        liquidity_state,
                        volume_state,
                        spread_state,
                        correlation_state,
                        sector_strength_state,
                        session_state,
                        confidence,
                        evidence_json,
                        source_version
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,
                        %s,%s,%s,%s,
                        'UNKNOWN',
                        'UNKNOWN',
                        %s,
                        0,
                        %s::jsonb,
                        %s
                    )
                    """,
                    (
                        symbol,
                        regime_code,
                        date.today(),
                        timeframe,
                        volatility_state,
                        liquidity_state,
                        volume_state,
                        spread_state,
                        session_state,
                        json.dumps(evidence, ensure_ascii=False),
                        SOURCE_VERSION,
                    ),
                )
                inserted += 1

    print("=== MARKET_CONTEXT_COLLECTOR_V1 ===")
    print(f"market_context_rows_inserted={inserted}")
    print("collector_mode=aggregate_existing_sources")
    print("edge_score_v2_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_CONTEXT_COLLECTOR_V1_READY")


if __name__ == "__main__":
    main()
