from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


@dataclass(frozen=True, slots=True)
class ThemeProperty:
    property_code: str
    property_value: str
    property_type: str
    description_key: str
    display_order: int


@dataclass(frozen=True, slots=True)
class ThemeModel:
    theme_code: str
    theme_name_key: str
    description_key: str
    properties: dict[str, ThemeProperty]

    def get(self, property_code: str, default: str = "") -> str:
        prop = self.properties.get(property_code)
        return prop.property_value if prop else default


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

                props = {
                    str(row["property_code"]): ThemeProperty(
                        property_code=str(row["property_code"]),
                        property_value=str(row["property_value"]),
                        property_type=str(row["property_type"]),
                        description_key=str(row["description_key"]),
                        display_order=int(row["display_order"]),
                    )
                    for row in cur.fetchall()
                }

        model = ThemeModel(
            theme_code=str(theme["theme_code"]),
            theme_name_key=str(theme["theme_name_key"]),
            description_key=str(theme["description_key"]),
            properties=props,
        )
        self._cache[key] = model
        return model
