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
