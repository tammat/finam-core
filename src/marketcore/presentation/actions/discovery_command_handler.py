from __future__ import annotations

import json
import os

import psycopg2


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)


def enqueue(command_code: str) -> None:

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO presentation.command_queue_v1 (

                    command_code,

                    payload,

                    source_version

                )

                VALUES (

                    %s,

                    %s,

                    'EDGE_DISCOVERY_CONTROL_UI_V1'

                )
                """,
                (
                    command_code,
                    json.dumps({}),
                ),
            )
