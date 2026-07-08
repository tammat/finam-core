from __future__ import annotations
from marketcore.presentation.components.common.html import h

def render_data_table(columns: list[tuple[str, str]], rows: list[dict], class_name: str = "data-table") -> str:
    header = "".join(f"<th>{h(label)}</th>" for _, label in columns)
    body = "".join("<tr>" + "".join(f"<td>{h(row.get(key))}</td>" for key, _ in columns) + "</tr>" for row in rows)
    return f'<table class="{h(class_name)} ui-data-table"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'
