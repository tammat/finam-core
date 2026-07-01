from __future__ import annotations

from html import escape

from marketcore.presentation.dashboard.i18n import normalize_language
from marketcore.presentation.dashboard.layout_components import (
    render_activity_feed,
    render_footer,
    render_header,
    render_mobile_navigation,
    render_sidebar,
    render_styles,
)
from marketcore.presentation.dashboard.layout_models import LayoutContent, LayoutState
from marketcore.presentation.dashboard.theme import normalize_theme
from marketcore.presentation.dashboard.timezone import normalize_timezone


class DashboardLayoutBuilder:
    def build(self, content: LayoutContent, state: LayoutState | None = None) -> str:
        state = state or LayoutState()
        normalized_state = LayoutState(
            lang=normalize_language(state.lang),
            timezone=normalize_timezone(state.timezone),
            theme=normalize_theme(state.theme),
            user_label=state.user_label,
        )

        return f"""<!doctype html>
<html lang="{escape(normalized_state.lang)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(content.title)} | Finam_Core</title>
  {render_styles()}
</head>
<body>
  {render_header(normalized_state)}
  <div class="fc-shell">
    {render_sidebar(normalized_state)}
    <main class="fc-content">
      {content.body_html}
    </main>
  </div>
  {render_activity_feed(normalized_state)}
  {render_footer(normalized_state)}
  {render_mobile_navigation(normalized_state)}
</body>
</html>"""
