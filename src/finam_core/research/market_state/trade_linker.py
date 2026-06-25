from datetime import timedelta

import psycopg2


class MarketStateTradeLinker:
    """
    Связывает сделки с ближайшими снимками состояния рынка.

    ВАЖНО:
    - только research.*;
    - Runtime не изменяется;
    - Execution не изменяется;
    - идемпотентная запись.
    """

    def __init__(self, database_url: str, max_snapshot_age_seconds: int = 300):
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        if database_url.startswith("sqlite"):
            raise ValueError("SQLite запрещен")

        self.database_url = database_url
        self.max_snapshot_age = timedelta(seconds=max_snapshot_age_seconds)

    def run(self) -> int:

        linked = 0

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    SELECT
                        trade_id,
                        symbol,
                        timeframe,
                        entry_ts,
                        exit_ts
                    FROM research.trade_facts
                    WHERE payload->>'trade_source_class'
                        ='RUNTIME_OR_PAPER_CLEAN_ENOUGH'
                    ORDER BY entry_ts;
                    """
                )

                trades = cur.fetchall()

                for trade in trades:

                    trade_id, symbol, timeframe, entry_ts, exit_ts = trade

                    cur.execute(
                        """
                        SELECT
                            snapshot_id,
                            compact_signature
                        FROM research.market_state_snapshots_v1
                        WHERE
                            symbol=%s
                            AND timeframe=%s
                            AND snapshot_ts<=%s
                        ORDER BY snapshot_ts DESC
                        LIMIT 1;
                        """,
                        (
                            symbol,
                            timeframe,
                            entry_ts,
                        ),
                    )

                    row = cur.fetchone()

                    if row is None:
                        continue

                    entry_snapshot_id, entry_signature = row

                    exit_snapshot_id = None
                    exit_signature = None

                    if exit_ts is not None:

                        cur.execute(
                            """
                            SELECT
                                snapshot_id,
                                compact_signature
                            FROM research.market_state_snapshots_v1
                            WHERE
                                symbol=%s
                                AND timeframe=%s
                                AND snapshot_ts<=%s
                            ORDER BY snapshot_ts DESC
                            LIMIT 1;
                            """,
                            (
                                symbol,
                                timeframe,
                                exit_ts,
                            ),
                        )

                        row2 = cur.fetchone()

                        if row2:
                            exit_snapshot_id, exit_signature = row2

                    cur.execute(
                        """
                        INSERT INTO research.trade_state_snapshots_v1
                        (
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
                        VALUES
                        (
                            %s,%s,%s,%s,%s,
                            %s,%s,%s,%s,
                            0,
                            %s,
                            %s
                        )

                        ON CONFLICT(trade_id)

                        DO UPDATE SET

                            entry_snapshot_id=EXCLUDED.entry_snapshot_id,
                            exit_snapshot_id=EXCLUDED.exit_snapshot_id,
                            entry_compact_signature=EXCLUDED.entry_compact_signature,
                            exit_compact_signature=EXCLUDED.exit_compact_signature,
                            link_quality=EXCLUDED.link_quality,
                            link_reason=EXCLUDED.link_reason;
                        """,
                        (
                            trade_id,
                            symbol,
                            timeframe,
                            entry_ts,
                            exit_ts,
                            entry_snapshot_id,
                            exit_snapshot_id,
                            entry_signature,
                            exit_signature,
                            "EXACT_OR_NEAREST_OK",
                            "runtime_shadow_market_state",
                        ),
                    )

                    linked += 1

            conn.commit()

        return linked
