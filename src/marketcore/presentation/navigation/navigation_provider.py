from __future__ import annotations

from dataclasses import dataclass
import os

import psycopg2
import psycopg2.extras


@dataclass(frozen=True, slots=True)
class NavigationItem:
    item_code: str
    group_code: str
    caption: str
    route: str
    icon: str
    display_order: int


@dataclass(frozen=True, slots=True)
class NavigationGroup:
    group_code: str
    caption: str
    icon: str
    display_order: int
    items: list[NavigationItem]


class NavigationProvider:
    def __init__(
        self,
        database_url: str | None = None,
        locale_code: str = "ru",
        workspace_role: str = "OPERATOR",
    ) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")
        self.locale_code = locale_code
        self.workspace_role = workspace_role

    def load(self) -> list[NavigationGroup]:
        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        g.group_code,
                        coalesce(gr.caption, g.group_code) AS group_caption,
                        g.icon AS group_icon,
                        g.display_order AS group_order,
                        i.item_code,
                        i.route,
                        i.icon AS item_icon,
                        i.display_order AS item_order,
                        coalesce(ir.caption, i.item_code) AS item_caption
                    FROM presentation.ui_navigation_group_v1 g
                    JOIN presentation.ui_navigation_item_v1 i
                      ON i.group_code=g.group_code
                     AND i.is_enabled=true
                    LEFT JOIN presentation.ui_resource_v1 gr
                      ON gr.resource_key=g.resource_key
                     AND gr.locale_code=%s
                    LEFT JOIN presentation.ui_resource_v1 ir
                      ON ir.resource_key=i.resource_key
                     AND ir.locale_code=%s
                    WHERE g.is_enabled=true
                      AND g.workspace_role=%s
                      AND i.workspace_role=%s
                    ORDER BY g.display_order, i.display_order;
                """, (
                    self.locale_code,
                    self.locale_code,
                    self.workspace_role,
                    self.workspace_role,
                ))
                rows = [dict(r) for r in cur.fetchall()]

        groups: dict[str, NavigationGroup] = {}

        for row in rows:
            group_code = row["group_code"]
            if group_code not in groups:
                groups[group_code] = NavigationGroup(
                    group_code=group_code,
                    caption=row["group_caption"],
                    icon=row["group_icon"],
                    display_order=int(row["group_order"]),
                    items=[],
                )

            groups[group_code].items.append(
                NavigationItem(
                    item_code=row["item_code"],
                    group_code=group_code,
                    caption=row["item_caption"],
                    route=row["route"],
                    icon=row["item_icon"],
                    display_order=int(row["item_order"]),
                )
            )

        return list(groups.values())
