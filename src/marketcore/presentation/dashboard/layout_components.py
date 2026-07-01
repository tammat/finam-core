from __future__ import annotations

from html import escape

from marketcore.presentation.dashboard.i18n import t
from marketcore.presentation.dashboard.navigation import navigation_items
from marketcore.presentation.dashboard.theme import normalize_theme
from marketcore.presentation.dashboard.timezone import normalize_timezone
from marketcore.presentation.dashboard.layout_models import LayoutState


def render_header(state: LayoutState) -> str:
    lang = escape(state.lang.upper())
    tz = escape(normalize_timezone(state.timezone))
    theme = escape(normalize_theme(state.theme))
    user = escape(state.user_label)

    return f"""
<header class="fc-header">
  <div class="fc-brand">
    <button class="fc-menu-btn" aria-label="Menu">☰</button>
    <strong>Finam_Core</strong>
  </div>
  <div class="fc-header-actions">
    <span>{lang}</span>
    <span>{tz}</span>
    <span>{theme}</span>
    <span>{user}</span>
  </div>
</header>
"""


def render_sidebar(state: LayoutState) -> str:
    items = navigation_items()
    links = []
    for item in items:
        title = escape(t(str(item["title_key"]), state.lang))
        path = escape(str(item["path"]))
        links.append(f'<a class="fc-nav-item" href="{path}">{title}</a>')

    return f"""
<aside class="fc-sidebar">
  <nav>
    {''.join(links)}
  </nav>
</aside>
"""


def render_mobile_navigation(state: LayoutState) -> str:
    items = [
        ("home", "/"),
        ("market", "/market"),
        ("research", "/research"),
        ("risk", "/risk"),
        ("system", "/system"),
    ]

    links = []
    for key, path in items:
        links.append(
            f'<a class="fc-mobile-nav-item" href="{escape(path)}">{escape(t(key, state.lang))}</a>'
        )

    return f"""
<nav class="fc-mobile-nav">
  {''.join(links)}
</nav>
"""


def render_activity_feed(state: LayoutState) -> str:
    title = escape(t("activity_feed", state.lang))
    empty = escape(t("no_events", state.lang))
    return f"""
<section class="fc-activity">
  <strong>{title}</strong>
  <span>{empty}</span>
</section>
"""


def render_footer(state: LayoutState) -> str:
    return """
<footer class="fc-footer">
  <span>Dashboard Layout V1</span>
  <span>runtime_changed=0</span>
  <span>micro_live_allowed=0</span>
</footer>
"""


def render_styles() -> str:
    return """
<style>
:root {
  --fc-bg: #f6f7f9;
  --fc-panel: #ffffff;
  --fc-border: #e5e7eb;
  --fc-text: #111827;
  --fc-muted: #6b7280;
  --fc-header: #111827;
  --fc-header-text: #ffffff;
}

body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: var(--fc-bg);
  color: var(--fc-text);
}

.fc-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--fc-header);
  color: var(--fc-header-text);
  padding: 0 16px;
}

.fc-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.fc-menu-btn {
  display: none;
  border: 0;
  background: transparent;
  color: white;
  font-size: 20px;
}

.fc-header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 13px;
}

.fc-shell {
  display: grid;
  grid-template-columns: 232px 1fr;
  min-height: calc(100vh - 56px - 44px - 40px);
}

.fc-sidebar {
  background: var(--fc-panel);
  border-right: 1px solid var(--fc-border);
  padding: 12px;
}

.fc-nav-item {
  display: block;
  padding: 10px 12px;
  margin-bottom: 4px;
  color: var(--fc-text);
  text-decoration: none;
  border-radius: 8px;
}

.fc-nav-item:hover {
  background: #f3f4f6;
}

.fc-content {
  padding: 20px;
}

.fc-card {
  background: var(--fc-panel);
  border: 1px solid var(--fc-border);
  border-radius: 12px;
  padding: 16px;
}

.fc-activity {
  min-height: 43px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 16px;
  background: var(--fc-panel);
  border-top: 1px solid var(--fc-border);
  color: var(--fc-muted);
}

.fc-footer {
  min-height: 39px;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 16px;
  background: var(--fc-panel);
  border-top: 1px solid var(--fc-border);
  color: var(--fc-muted);
  font-size: 12px;
}

.fc-mobile-nav {
  display: none;
}

@media (max-width: 1023px) {
  .fc-shell {
    grid-template-columns: 180px 1fr;
  }
}

@media (max-width: 767px) {
  .fc-menu-btn {
    display: inline-block;
  }

  .fc-header {
    padding: 0 12px;
  }

  .fc-header-actions {
    gap: 8px;
    font-size: 11px;
  }

  .fc-shell {
    display: block;
    min-height: auto;
  }

  .fc-sidebar {
    display: none;
  }

  .fc-content {
    padding: 12px;
    padding-bottom: 72px;
  }

  .fc-mobile-nav {
    display: flex;
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    height: 56px;
    background: var(--fc-panel);
    border-top: 1px solid var(--fc-border);
    justify-content: space-around;
    align-items: center;
    z-index: 20;
  }

  .fc-mobile-nav-item {
    color: var(--fc-text);
    text-decoration: none;
    font-size: 11px;
  }

  .fc-activity {
    display: block;
    padding: 12px;
  }

  .fc-footer {
    display: block;
    padding: 12px;
    padding-bottom: 68px;
  }
}
</style>
"""
