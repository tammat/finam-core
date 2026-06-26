from __future__ import annotations

import psycopg2
import psycopg2.extras

from marketcore.catalog.discovery.context import DiscoveryContext
from marketcore.catalog.discovery.result import DiscoveredObject


def layer_from_name(name: str) -> str:
    if name.startswith("qlt_"):
        return "QUALITY"
    if name.startswith("nrm_"):
        return "NORMALIZED"
    if name.startswith("fact_event_"):
        return "EVENT_FACT"
    if name.startswith("fact_state_"):
        return "STATE_FACT"
    if name.startswith("dim_"):
        return "DIMENSION"
    if name.startswith("sem_"):
        return "SEMANTIC"
    if name.startswith("mart_"):
        return "MART"
    if name.startswith("snap_"):
        return "SNAPSHOT"
    if name.startswith("ref_"):
        return "REFERENCE"
    if name.startswith("raw_"):
        return "RAW"
    return "LEGACY"


def object_type_from_table_type(table_type: str) -> str:
    if table_type == "BASE TABLE":
        return "DATASET"
    if table_type == "VIEW":
        return "DATASET"
    return "DATASET"


class PostgresDiscovery:
    name = "PostgresDiscovery"
    version = "POSTGRES_DISCOVERY_PLUGIN_V1"

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url

    def discover(self, context: DiscoveryContext) -> list[DiscoveredObject]:
        objects: list[DiscoveredObject] = []

        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT table_schema, table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = ANY(%s)
                      AND (
                          table_name LIKE ANY(%s)
                          OR %s = 'ALL'
                      )
                    ORDER BY table_schema, table_name
                    """,
                    (
                        list(context.schema_filter),
                        list(context.name_patterns),
                        "ALL" if context.name_patterns == ("ALL",) else "",
                    ),
                )
                table_rows = cur.fetchall()

                for row in table_rows:
                    schema_name = row["table_schema"]
                    table_name = row["table_name"]

                    rows_count = None
                    if schema_name not in ("information_schema", "pg_catalog"):
                        try:
                            cur.execute(
                                f'SELECT count(*)::bigint AS cnt FROM "{schema_name}"."{table_name}"'
                            )
                            rows_count = int(cur.fetchone()["cnt"])
                        except Exception:
                            conn.rollback()
                            rows_count = None

                    category = "TABLE" if row["table_type"] == "BASE TABLE" else "VIEW"
                    layer = layer_from_name(table_name)

                    objects.append(
                        DiscoveredObject(
                            object_id=f"postgres:{schema_name}.{table_name}",
                            object_name=table_name,
                            domain=context.domain,
                            category=category,
                            object_type=object_type_from_table_type(row["table_type"]),
                            schema_name=schema_name,
                            warehouse_layer=layer,
                            rows_count=rows_count,
                            discovery_source=self.name,
                            discovery_version=self.version,
                            payload={
                                "table_type": row["table_type"],
                                "profile": context.profile,
                            },
                        )
                    )

                cur.execute(
                    """
                    SELECT routine_schema, routine_name, routine_type
                    FROM information_schema.routines
                    WHERE routine_schema = ANY(%s)
                    ORDER BY routine_schema, routine_name
                    """,
                    (list(context.schema_filter),),
                )

                for row in cur.fetchall():
                    schema_name = row["routine_schema"]
                    routine_name = row["routine_name"]

                    objects.append(
                        DiscoveredObject(
                            object_id=f"postgres:{schema_name}.{routine_name}",
                            object_name=routine_name,
                            domain=context.domain,
                            category="FUNCTION",
                            object_type="PROCESS",
                            schema_name=schema_name,
                            warehouse_layer="LEGACY",
                            rows_count=None,
                            discovery_source=self.name,
                            discovery_version=self.version,
                            payload={
                                "routine_type": row["routine_type"],
                                "profile": context.profile,
                            },
                        )
                    )

        return objects
