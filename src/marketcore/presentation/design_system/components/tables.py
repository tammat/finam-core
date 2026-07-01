from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.registry import DesignComponent, design_registry
from marketcore.presentation.formatters.status_formatter import StatusFormatter


def _display_cell(value: object) -> str:
    text = str(value)
    normalized = text.upper()
    if normalized in {"READY", "WARNING", "HIGH", "CRITICAL", "DISABLED", "INFO", "SAFE"}:
        return StatusFormatter.short(normalized, "ru")
    return text


def TableCard(title: str, columns: list[str], rows: list[list[object]]) -> str:
    head = "".join(f"<th>{escape(str(c))}</th>" for c in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(_display_cell(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )

    return (
        '<section class="fc-card">'
        f"<h3>{escape(str(title))}</h3>"
        '<div class="fc-table-wrap">'
        "<table>"
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</div>"
        "</section>"
    )


design_registry.register(DesignComponent("TableCard", "tables"))
