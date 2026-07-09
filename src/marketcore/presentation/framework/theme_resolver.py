from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras

from marketcore.presentation.framework.mapper.theme_mapper import ThemeModelMapper


from marketcore.presentation.framework.theme_model import ThemeModel

class ThemeResolverV1:
    def __init__(self) -> None:
        self._cache: dict[str, ThemeModel] = {}

    def resolve(self, theme_code: str = "DEFAULT") -> ThemeModel:
        key = theme_code.strip().upper() or "DEFAULT"
        if key in self._cache:
            return self._cache[key]

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT theme_code, theme_name_key, description_key
                    FROM presentation.ui_theme_v1
                    WHERE theme_code=%s
                      AND enabled
                    LIMIT 1
                    """,
                    (key,),
                )
                theme = cur.fetchone()

                if not theme:
                    cur.execute(
                        """
                        SELECT theme_code, theme_name_key, description_key
                        FROM presentation.ui_theme_v1
                        WHERE is_default
                          AND enabled
                        ORDER BY theme_code
                        LIMIT 1
                        """
                    )
                    theme = cur.fetchone()

                if not theme:
                    raise RuntimeError("UI_THEME_NOT_FOUND")

                cur.execute(
                    """
                    SELECT property_code, property_value, property_type,
                           description_key, display_order
                    FROM presentation.ui_theme_property_v1
                    WHERE theme_code=%s
                    ORDER BY display_order, property_code
                    """,
                    (theme["theme_code"],),
                )

                property_rows = list(cur.fetchall())

        model = ThemeModelMapper.with_properties(theme, property_rows)
        self._cache[key] = model
        return model
