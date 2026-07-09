from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.framework.registry import UiStatusCode


@dataclass(frozen=True, slots=True)
class HomeStatusItemV1:
    item_code: str
    title_key: str
    subtitle_key: str
    status_code: UiStatusCode
    status_label_key: str
    rows_total: int
    updated_at: str
