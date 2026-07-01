from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.registry import DesignComponent, design_registry


def TableCard(title: str, columns: list[str], rows: list[list[str | int | float]]) -> str:
    head = "".join(f"<th>{escape(str(c))}</th>" for c in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return (
        '<section class="fc-card fc-table-card">'
        f'<h3>{escape(title)}</h3>'
        '<table>'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table>'
        '</section>'
    )


design_registry.register(DesignComponent("TableCard", "tables"))
