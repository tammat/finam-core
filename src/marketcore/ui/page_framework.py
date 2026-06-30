from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Callable

RenderFn = Callable[[], str]


@dataclass(frozen=True)
class Section:
    section_id: str
    title: str
    renderer: RenderFn


@dataclass(frozen=True)
class Page:
    page_id: str
    title: str
    route: str
    group: str
    sections: tuple[Section, ...]
    read_only: bool = True


def escape_html(value: Any) -> str:
    return escape("" if value is None else str(value))


def render_card(title: str, value: Any, status: str = "READY") -> str:
    return (
        '<div class="mc-card">'
        f'<div class="mc-card-title">{escape_html(title)}</div>'
        f'<div class="mc-card-value">{escape_html(value)}</div>'
        f'<div class="mc-card-status">{escape_html(status)}</div>'
        '</div>'
    )


def render_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="mc-muted">Нет данных</p>'

    columns = list(rows[0].keys())
    head = "".join(f"<th>{escape_html(c)}</th>" for c in columns)
    body = ""

    for row in rows:
        cells = "".join(
            f'<td data-label="{escape_html(c)}">{escape_html(row.get(c))}</td>'
            for c in columns
        )
        body += f"<tr>{cells}</tr>"

    return (
        '<div class="mc-table-wrap">'
        '<table class="mc-table">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</div>"
    )


def render_navigation(pages: list[Page], active_route: str) -> str:
    items = []
    for page in pages:
        active = " mc-active" if page.route == active_route else ""
        items.append(
            f'<a class="mc-nav-item{active}" href="{escape_html(page.route)}">'
            f"{escape_html(page.title)}</a>"
        )
    return '<nav class="mc-nav">' + "".join(items) + "</nav>"


def render_page(page: Page, pages: list[Page] | None = None) -> str:
    nav = render_navigation(pages or [page], page.route)
    mode = "READ_ONLY" if page.read_only else "WRITE_ENABLED"

    sections_html = ""
    for section in page.sections:
        sections_html += (
            f'<section id="{escape_html(section.section_id)}" class="mc-section">'
            f"<h2>{escape_html(section.title)}</h2>"
            f"{section.renderer()}"
            "</section>"
        )

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{escape_html(page.title)}</title>
<style>
:root {{
  --bg: #f6f7f9;
  --card: #ffffff;
  --text: #1f2937;
  --muted: #6b7280;
  --border: #d7dce2;
  --active: #111827;
}}

* {{
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
}}

body {{
  margin: 0;
  padding: env(safe-area-inset-top) 14px env(safe-area-inset-bottom) 14px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 16px;
}}

.mc-container {{
  max-width: 1180px;
  margin: 0 auto;
  padding: 16px 0 32px;
}}

.mc-header {{
  margin-bottom: 14px;
}}

.mc-header h1 {{
  margin: 0 0 8px;
  font-size: 28px;
  line-height: 1.2;
}}

.mc-meta {{
  color: var(--muted);
  font-size: 13px;
  overflow-wrap: anywhere;
}}

.mc-nav {{
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 4px 0 12px;
  margin-bottom: 10px;
  -webkit-overflow-scrolling: touch;
}}

.mc-nav-item {{
  flex: 0 0 auto;
  min-height: 40px;
  padding: 10px 12px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  text-decoration: none;
  color: var(--text);
  font-size: 15px;
}}

.mc-active {{
  font-weight: 700;
  border-color: var(--active);
}}

.mc-section {{
  background: var(--card);
  padding: 14px;
  margin: 12px 0;
  border-radius: 14px;
  border: 1px solid var(--border);
}}

.mc-section h2 {{
  margin: 0 0 12px;
  font-size: 20px;
}}

.mc-card {{
  display: inline-block;
  vertical-align: top;
  min-width: 150px;
  width: calc(25% - 12px);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px;
  margin: 6px;
}}

.mc-card-title {{
  font-size: 12px;
  color: var(--muted);
}}

.mc-card-value {{
  font-size: 24px;
  font-weight: 700;
  margin-top: 4px;
}}

.mc-card-status {{
  font-size: 11px;
  margin-top: 8px;
  color: var(--muted);
}}

.mc-table-wrap {{
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}}

.mc-table {{
  border-collapse: collapse;
  width: 100%;
  min-width: 620px;
  background: var(--card);
}}

.mc-table th,
.mc-table td {{
  border: 1px solid var(--border);
  padding: 9px;
  text-align: left;
  vertical-align: top;
}}

.mc-table th {{
  background: #eef1f5;
}}

.mc-muted {{
  color: var(--muted);
}}

@media (max-width: 768px) {{
  body {{
    padding-left: 10px;
    padding-right: 10px;
    font-size: 15px;
  }}

  .mc-header h1 {{
    font-size: 24px;
  }}

  .mc-card {{
    width: calc(50% - 12px);
    min-width: 0;
  }}

  .mc-section {{
    padding: 12px;
    border-radius: 12px;
  }}
}}

@media (max-width: 480px) {{
  .mc-card {{
    width: 100%;
    margin-left: 0;
    margin-right: 0;
  }}

  .mc-table {{
    min-width: 0;
  }}

  .mc-table thead {{
    display: none;
  }}

  .mc-table,
  .mc-table tbody,
  .mc-table tr,
  .mc-table td {{
    display: block;
    width: 100%;
  }}

  .mc-table tr {{
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 10px;
    overflow: hidden;
  }}

  .mc-table td {{
    border: 0;
    border-bottom: 1px solid var(--border);
    padding: 10px;
  }}

  .mc-table td::before {{
    content: attr(data-label);
    display: block;
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 3px;
  }}
}}
</style>
</head>
<body>
<div class="mc-container">
  <div class="mc-header">
    <h1>{escape_html(page.title)}</h1>
    <div class="mc-meta">route={escape_html(page.route)} | group={escape_html(page.group)} | mode={mode}</div>
  </div>
  {nav}
  {sections_html}
</div>
</body>
</html>
"""
