from __future__ import annotations

from functools import lru_cache
from html import escape

import psycopg2
import psycopg2.extras


@lru_cache(maxsize=4096)
def translate(resource_key: str, locale_code: str = "ru") -> str:
    if not resource_key:
        return ""

    try:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT caption
                    FROM presentation.ui_resource_v1
                    WHERE resource_key=%s
                      AND locale_code=%s
                    LIMIT 1
                    """,
                    (resource_key, locale_code),
                )
                row = cur.fetchone()
                if row and row.get("caption"):
                    return str(row["caption"])
    except Exception:
        return resource_key

    return resource_key


def tr(resource_key: str, locale_code: str = "ru") -> str:
    return escape(translate(resource_key, locale_code))
