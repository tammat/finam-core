from __future__ import annotations

from marketcore.presentation.components.html import h


def render_data_table(columns: list[str], rows: list[dict]) -> str:
    head = "".join(f"<th>{h(col)}</th>" for col in columns)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{h(row.get(col, ''))}</td>" for col in columns) + "</tr>"

    return (
        '<div class="table-wrap">'
        '<table class="data-table">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</div>"
    )
