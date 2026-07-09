from __future__ import annotations

from typing import Iterable

import psycopg2
import psycopg2.extras

from marketcore.presentation.framework.i18n_model import UiTextModel
from marketcore.presentation.framework.mapper.i18n_mapper import UiTextMapper


class UiI18nResolverV1:
    def __init__(self, locale_code: str = "ru") -> None:
        self._locale_code = locale_code
        self._cache: dict[str, UiTextModel] = {}

    def text(self, resource_key: str, mode: str = "caption") -> str:
        item = self.resolve(resource_key)
        if mode == "short":
            return item.caption_short
        if mode == "mobile":
            return item.caption_mobile
        if mode == "tooltip":
            return item.tooltip
        if mode == "icon":
            return item.icon
        return item.caption

    def resolve(self, resource_key: str) -> UiTextModel:
        key = resource_key.strip()
        if key in self._cache:
            return self._cache[key]

        loaded = self.resolve_many([key])
        return loaded[key]

    def resolve_many(self, resource_keys: Iterable[str]) -> dict[str, UiTextModel]:
        keys = tuple(dict.fromkeys(k.strip() for k in resource_keys if k and k.strip()))
        missing = [key for key in keys if key not in self._cache]

        if missing:
            self._load_missing(missing)

        return {key: self._cache[key] for key in keys}

    def _load_missing(self, resource_keys: list[str]) -> None:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        resource_key,
                        locale_code,
                        caption,
                        caption_short,
                        caption_mobile,
                        tooltip,
                        icon
                    FROM presentation.ui_resource_v1
                    WHERE locale_code=%s
                      AND resource_key = ANY(%s)
                    """,
                    (self._locale_code, resource_keys),
                )
                rows = UiTextMapper.from_rows(cur.fetchall())

        found = {row.resource_key: row for row in rows}

        for key in resource_keys:
            self._cache[key] = found.get(
                key,
                UiTextModel(
                    resource_key=key,
                    locale_code=self._locale_code,
                    caption=key,
                    caption_short=key,
                    caption_mobile=key,
                    tooltip="",
                    icon="",
                ),
            )
