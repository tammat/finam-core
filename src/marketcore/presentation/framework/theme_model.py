from __future__ import annotations

from dataclasses import dataclass


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
