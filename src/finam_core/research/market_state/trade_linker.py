import psycopg2


class MarketStateTradeLinker:
    """
    Связывает public.trade_outcomes с ближайшими Market State Snapshot.

    Источник сделок V1.1:
    - public.trade_outcomes;
    - research.trade_facts не требуется.

    Ограничения:
    - только research.*;
    - Runtime не изменяется;
    - Execution не изменяется;
    - заявки не отправляются.
    """

    def __init__(self, database_url: str):
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        if database_url.startswith("sqlite"):
            raise ValueError("SQLite запрещен")
        self.database_url = database_url

    def _table_exists(self, cur, schema: str, table: str) -> bool:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema=%s
                  AND table_name=%s
            );
            """,
            (schema, table),
        )
        return bool(cur.fetchone()[0])

    def run(self) -> int:
        linked = 0

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                if not self._table_exists(cur, "public", "trade_outcomes"):
                    print("BLOCKER=PUBLIC_TRADE_OUTCOMES_NOT_FOUND")
                    print("linked_rows=0")
                    return 0

                cur.execute(
                    """
                    SELECT
                        id::text AS trade_id,
                        symbol,
                        timeframe,
                        entry_ts,
                        exit_ts
                    FROM public.trade_outcomes
                    WHERE symbol IS NOT NULL
                      AND entry_ts IS NOT NULL
                    ORDER BY entry_ts;
                    """
                )

                trades = cur.fetchall()

                for trade_id, symbol, timeframe, entry_ts, exit_ts in trades:
                    effective_timeframe = timeframe or "UNKNOWN"

                    cur.execute(
                        """
                        SELECT snapshot_id, compact_signature
                        FROM research.market_state_snapshots_v1
                        WHERE symbol=%s
                          AND timeframe=%s
                          AND snapshot_ts<=%s
                        ORDER BY snapshot_ts DESC
                        LIMIT 1;
                        """,
                        (symbol, effective_timeframe, entry_ts),
                    )

                    entry_row = cur.fetchone()

                    if not entry_row:
                        cur.execute(
                            """
                            INSERT INTO research.trade_state_snapshots_v1 (
                                trade_id,
                                symbol,
                                timeframe,
                                entry_ts,
                                exit_ts,
                                link_quality,
                                link_reason
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT(trade_id)
                            DO UPDATE SET
                                link_quality=EXCLUDED.link_quality,
                                link_reason=EXCLUDED.link_reason;
                            """,
                            (
                                trade_id,
                                symbol,
                                effective_timeframe,
                                entry_ts,
                                exit_ts,
                                "NO_SNAPSHOT",
                                "no_entry_snapshot_found_in_market_state_snapshots_v1",
                            ),
                        )
                        linked += 1
                        continue

                    entry_snapshot_id, entry_signature = entry_row

                    exit_snapshot_id = None
                    exit_signature = None

                    if exit_ts is not None:
                        cur.execute(
                            """
                            SELECT snapshot_id, compact_signature
                            FROM research.market_state_snapshots_v1
                            WHERE symbol=%s
                              AND timeframe=%s
                              AND snapshot_ts<=%s
                            ORDER BY snapshot_ts DESC
                            LIMIT 1;
                            """,
                            (symbol, effective_timeframe, exit_ts),
                        )
                        exit_row = cur.fetchone()
                        if exit_row:
                            exit_snapshot_id, exit_signature = exit_row

                    link_quality = "EXACT_OR_NEAREST_OK"
                    link_reason = "linked_from_public_trade_outcomes_to_runtime_shadow_market_state"

                    if exit_ts is not None and exit_snapshot_id is None:
                        link_quality = "ENTRY_ONLY"
                        link_reason = "entry_snapshot_found_exit_snapshot_missing"

                    cur.execute(
                        """
                        INSERT INTO research.trade_state_snapshots_v1 (
                            trade_id,
                            symbol,
                            timeframe,
                            entry_ts,
                            exit_ts,
                            entry_snapshot_id,
                            exit_snapshot_id,
                            entry_compact_signature,
                            exit_compact_signature,
                            holding_snapshot_count,
                            link_quality,
                            link_reason
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,%s,%s)
                        ON CONFLICT(trade_id)
                        DO UPDATE SET
                            symbol=EXCLUDED.symbol,
                            timeframe=EXCLUDED.timeframe,
                            entry_ts=EXCLUDED.entry_ts,
                            exit_ts=EXCLUDED.exit_ts,
                            entry_snapshot_id=EXCLUDED.entry_snapshot_id,
                            exit_snapshot_id=EXCLUDED.exit_snapshot_id,
                            entry_compact_signature=EXCLUDED.entry_compact_signature,
                            exit_compact_signature=EXCLUDED.exit_compact_signature,
                            holding_snapshot_count=EXCLUDED.holding_snapshot_count,
                            link_quality=EXCLUDED.link_quality,
                            link_reason=EXCLUDED.link_reason;
                        """,
                        (
                            trade_id,
                            symbol,
                            effective_timeframe,
                            entry_ts,
                            exit_ts,
                            entry_snapshot_id,
                            exit_snapshot_id,
                            entry_signature,
                            exit_signature,
                            link_quality,
                            link_reason,
                        ),
                    )

                    linked += 1

            conn.commit()

        print(f"linked_rows={linked}")
        return linked
