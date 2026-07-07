from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2
import psycopg2.extras


@dataclass(frozen=True, slots=True)
class UiResource:
    resource_key: str
    locale_code: str
    caption: str
    tooltip: str
    icon: str
    hotkey: str
    resource_group: str


class UiResourceProvider:
    def __init__(self, database_url: str | None = None, locale_code: str = "ru") -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")
        self.locale_code = locale_code
        self._cache: dict[str, UiResource] = {}

    def load_group(self, resource_group: str) -> dict[str, UiResource]:
        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        resource_key,
                        locale_code,
                        caption,
                        tooltip,
                        icon,
                        hotkey,
                        resource_group
                    FROM presentation.ui_resource_v1
                    WHERE locale_code=%s
                      AND resource_group=%s
                      AND is_active=true
                    ORDER BY resource_key;
                    """,
                    (self.locale_code, resource_group),
                )
                rows = cur.fetchall()

        result: dict[str, UiResource] = {}
        for row in rows:
            resource = UiResource(
                resource_key=row["resource_key"],
                locale_code=row["locale_code"],
                caption=row["caption"],
                tooltip=row["tooltip"],
                icon=row["icon"],
                hotkey=row["hotkey"],
                resource_group=row["resource_group"],
            )
            result[resource.resource_key] = resource
            self._cache[resource.resource_key] = resource

        return result

    def tr(self, resource_key: str, fallback: str = "") -> str:
        resource = self._cache.get(resource_key)
        if resource is not None:
            return resource.caption
        return fallback or resource_key

    def tooltip(self, resource_key: str, fallback: str = "") -> str:
        resource = self._cache.get(resource_key)
        if resource is not None:
            return resource.tooltip
        return fallback

    def icon(self, resource_key: str, fallback: str = "") -> str:
        resource = self._cache.get(resource_key)
        if resource is not None:
            return resource.icon
        return fallback
