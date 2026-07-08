from __future__ import annotations

from marketcore.presentation.components.common.html import h


OPERATOR_SIDEBAR_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("/", "🧠", "Рабочее место"),
    ("/max-edge", "🎯", "Лучший Edge"),
    ("/edge-score-shadow", "👁️", "Shadow"),
    ("/edge-score-shadow-daily", "📊", "Аналитика"),
    ("/market-model", "🌍", "Рынок"),
    ("/portfolio", "💼", "Портфель"),
    ("/risk", "⚠", "Риски"),
    ("/system", "⚙", "Система"),
    ("/settings", "🔧", "Настройки"),
)


def render_sidebar(current_route: str = "/") -> str:
    links = []
    for route, icon, label in OPERATOR_SIDEBAR_ITEMS:
        cls = "active" if route == current_route else ""
        links.append(
            f'<a class="{h(cls)}" href="{h(route)}">'
            f'<span class="sidebar-icon">{h(icon)}</span>'
            f'<span class="sidebar-label">{h(label)}</span>'
            '</a>'
        )

    return f"""
    <nav class="sidebar operator-sidebar">
        <div class="sidebar-title">MarketCore</div>
        {''.join(links)}
    </nav>
    """
