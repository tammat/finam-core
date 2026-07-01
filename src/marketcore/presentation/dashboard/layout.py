from __future__ import annotations

from marketcore.presentation.dashboard.layout_builder import DashboardLayoutBuilder
from marketcore.presentation.dashboard.layout_models import LayoutContent, LayoutState


def render_shell(content: str, lang: str = "ru", timezone: str = "Europe/Moscow") -> str:
    builder = DashboardLayoutBuilder()
    return builder.build(
        LayoutContent(
            title="Dashboard",
            body_html=content,
        ),
        LayoutState(
            lang=lang,
            timezone=timezone,
            theme="light",
            user_label="Observer",
        ),
    )
