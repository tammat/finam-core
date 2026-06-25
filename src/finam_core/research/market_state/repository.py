import json
from datetime import datetime, timezone
from typing import Any

import psycopg2
from psycopg2.extras import Json

from finam_core.research.events import MarketStateBuiltEvent


class MarketStateRepository:
    # Репозиторий записи Market State Snapshot в PostgreSQL.
    # Пишет только в research.* и не зависит от Runtime/Execution.

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        if database_url.startswith("sqlite"):
            raise ValueError("SQLite запрещен: требуется PostgreSQL")
        self.database_url = database_url

    def save_market_state_event(
        self,
        event: MarketStateBuiltEvent,
        *,
        snapshot_ts: datetime | None = None,
        asset_class: str | None = None,
        source: str = "market_state_engine_v1",
        ontology_version: str = "market_state_ontology_v1",
        research_version: str = "research_platform_v1",
        engine_version: str = "MarketStateEngineCoreV1",
    ) -> int:
        # Идемпотентно сохраняет snapshot, values и metadata.
        ts = snapshot_ts or datetime.now(timezone.utc)
        classifier_versions = self._classifier_versions(event)

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO research.market_state_snapshots_v1 (
                        snapshot_ts,
                        symbol,
                        asset_class,
                        timeframe,
                        canonical_signature,
                        compact_signature,
                        quality,
                        confidence,
                        conflict_score,
                        source
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (snapshot_ts, symbol, timeframe, compact_signature)
                    DO UPDATE SET
                        quality = EXCLUDED.quality,
                        confidence = EXCLUDED.confidence,
                        conflict_score = EXCLUDED.conflict_score
                    RETURNING snapshot_id;
                    """,
                    (
                        ts,
                        event.symbol,
                        asset_class,
                        event.timeframe,
                        event.canonical_signature,
                        event.compact_signature,
                        event.quality,
                        event.confidence,
                        event.payload.get("conflict_score"),
                        source,
                    ),
                )
                snapshot_id = int(cur.fetchone()[0])

                for item in event.payload.get("classifier_results", []):
                    cur.execute(
                        """
                        INSERT INTO research.market_state_snapshot_values_v1 (
                            snapshot_id,
                            state_group,
                            state_code,
                            confidence,
                            classifier_version,
                            explanation_ru
                        )
                        VALUES (%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (snapshot_id, state_group)
                        DO UPDATE SET
                            state_code = EXCLUDED.state_code,
                            confidence = EXCLUDED.confidence,
                            classifier_version = EXCLUDED.classifier_version,
                            explanation_ru = EXCLUDED.explanation_ru;
                        """,
                        (
                            snapshot_id,
                            item.get("group"),
                            item.get("state"),
                            item.get("confidence"),
                            item.get("classifier_version"),
                            item.get("explanation_ru", ""),
                        ),
                    )

                cur.execute(
                    """
                    INSERT INTO research.market_state_snapshot_metadata_v1 (
                        snapshot_id,
                        ontology_version,
                        research_version,
                        engine_version,
                        classifier_versions,
                        explanation_tree_ru,
                        created_by
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (snapshot_id)
                    DO UPDATE SET
                        ontology_version = EXCLUDED.ontology_version,
                        research_version = EXCLUDED.research_version,
                        engine_version = EXCLUDED.engine_version,
                        classifier_versions = EXCLUDED.classifier_versions,
                        explanation_tree_ru = EXCLUDED.explanation_tree_ru;
                    """,
                    (
                        snapshot_id,
                        ontology_version,
                        research_version,
                        engine_version,
                        Json(classifier_versions),
                        Json(event.payload.get("explanation_tree_ru", [])),
                        source,
                    ),
                )

            conn.commit()

        return snapshot_id

    def _classifier_versions(self, event: MarketStateBuiltEvent) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in event.payload.get("classifier_results", []):
            group = str(item.get("group", "UNKNOWN"))
            version = str(item.get("classifier_version", "UNKNOWN"))
            result[group] = version
        return result
