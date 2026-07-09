from __future__ import annotations

from typing import Any

from marketcore.presentation.framework.mapper.base_mapper import BaseMapper
from marketcore.presentation.framework.theme_model import ThemeModel, ThemeProperty


class ThemeColumn:
    THEME_CODE = "theme_code"
    THEME_NAME_KEY = "theme_name_key"
    DESCRIPTION_KEY = "description_key"
    PROPERTY_CODE = "property_code"
    PROPERTY_VALUE = "property_value"
    PROPERTY_TYPE = "property_type"
    DISPLAY_ORDER = "display_order"


class ThemePropertyMapper(BaseMapper):
    @classmethod
    def from_db(cls, row: Any) -> ThemeProperty:
        return ThemeProperty(
            property_code=str(row[ThemeColumn.PROPERTY_CODE]),
            property_value=str(row[ThemeColumn.PROPERTY_VALUE]),
            property_type=str(row[ThemeColumn.PROPERTY_TYPE]),
            description_key=str(row[ThemeColumn.DESCRIPTION_KEY]),
            display_order=int(row[ThemeColumn.DISPLAY_ORDER]),
        )


class ThemeModelMapper(BaseMapper):
    @classmethod
    def from_db(cls, row: Any) -> ThemeModel:
        return ThemeModel(
            theme_code=str(row[ThemeColumn.THEME_CODE]),
            theme_name_key=str(row[ThemeColumn.THEME_NAME_KEY]),
            description_key=str(row[ThemeColumn.DESCRIPTION_KEY]),
            properties={},
        )

    @classmethod
    def with_properties(
        cls,
        theme_row: Any,
        property_rows: list[Any],
    ) -> ThemeModel:
        theme = cls.from_db(theme_row)
        properties = {
            item.property_code: item
            for item in ThemePropertyMapper.from_rows(property_rows)
        }
        return ThemeModel(
            theme_code=theme.theme_code,
            theme_name_key=theme.theme_name_key,
            description_key=theme.description_key,
            properties=properties,
        )
