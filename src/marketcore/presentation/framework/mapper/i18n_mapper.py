from __future__ import annotations

from typing import Any

from marketcore.presentation.framework.i18n_model import UiTextModel
from marketcore.presentation.framework.mapper.base_mapper import BaseMapper


class UiResourceColumn:
    RESOURCE_KEY = "resource_key"
    LOCALE_CODE = "locale_code"
    CAPTION = "caption"
    CAPTION_SHORT = "caption_short"
    CAPTION_MOBILE = "caption_mobile"
    TOOLTIP = "tooltip"
    ICON = "icon"


class UiTextMapper(BaseMapper):
    @classmethod
    def from_db(cls, row: Any) -> UiTextModel:
        return UiTextModel(
            resource_key=str(row[UiResourceColumn.RESOURCE_KEY]),
            locale_code=str(row[UiResourceColumn.LOCALE_CODE]),
            caption=str(row.get(UiResourceColumn.CAPTION) or row[UiResourceColumn.RESOURCE_KEY]),
            caption_short=str(row.get(UiResourceColumn.CAPTION_SHORT) or row.get(UiResourceColumn.CAPTION) or row[UiResourceColumn.RESOURCE_KEY]),
            caption_mobile=str(row.get(UiResourceColumn.CAPTION_MOBILE) or row.get(UiResourceColumn.CAPTION_SHORT) or row.get(UiResourceColumn.CAPTION) or row[UiResourceColumn.RESOURCE_KEY]),
            tooltip=str(row.get(UiResourceColumn.TOOLTIP) or ""),
            icon=str(row.get(UiResourceColumn.ICON) or ""),
        )
