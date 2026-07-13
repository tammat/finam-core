from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.render_tree.node_types import RenderNodeType
from marketcore.presentation.render_tree.render_node import RenderNode


@dataclass(frozen=True, slots=True)
class DataTableColumn:
    key: str
    label: str


def data_table_node(
    columns: tuple[DataTableColumn, ...],
    rows: tuple[dict[str, object], ...],
    *,
    class_name: str = "mc-oos-table",
) -> RenderNode:
    header = RenderNode(
        RenderNodeType.TABLE_HEAD,
        children=(
            RenderNode(
                RenderNodeType.TABLE_ROW,
                children=tuple(
                    RenderNode(RenderNodeType.TABLE_HEADER_CELL, text=column.label)
                    for column in columns
                ),
            ),
        ),
    )
    body = RenderNode(
        RenderNodeType.TABLE_BODY,
        children=tuple(
            RenderNode(
                RenderNodeType.TABLE_ROW,
                props={
                    **({"data-status": str(row["_status"])} if row.get("_status") else {}),
                    **({"activation_target": str(row["_activation_target"])} if row.get("_activation_target") else {}),
                    **({"aria_label": str(row["_aria_label"])} if row.get("_aria_label") else {}),
                    **({"progress_label": str(row["_progress_label"])} if row.get("_progress_label") else {}),
                    **({"progress_complete_label": str(row["_progress_complete_label"])} if row.get("_progress_complete_label") else {}),
                    **({"confirmation_options": str(row["_confirmation_options"])} if row.get("_confirmation_options") else {}),
                    **({"confirmation_title": str(row["_confirmation_title"])} if row.get("_confirmation_title") else {}),
                    **({"confirmation_label": str(row["_confirmation_label"])} if row.get("_confirmation_label") else {}),
                    **({"role": "link", "tab_index": 0} if row.get("_activation_target") else {}),
                },
                children=tuple(
                    RenderNode(RenderNodeType.TABLE_CELL, text=str(row.get(column.key, "")))
                    for column in columns
                ),
            )
            for row in rows
        ),
    )
    return RenderNode(
        RenderNodeType.TABLE,
        props={"class": class_name},
        children=(header, body),
    )
