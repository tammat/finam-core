from __future__ import annotations

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.render_tree.node_types import RenderNodeType
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
from marketcore.presentation.workspace_v2.viewmodel.home_v2_viewmodel import (
    HomeV2ViewModel,
)


def render_home_v2(
    vm: HomeV2ViewModel,
    locale_code: str = "ru",
) -> RenderDocument:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    layout = vm.layout

    section_nodes: list[RenderNode] = []

    for section in layout.ordered_sections():
        card_nodes: list[RenderNode] = []

        for card in section.ordered_cards():
            target = ""

            if card.actions:
                target = str(card.actions[0].get("target", ""))

            card_children: list[RenderNode] = [
                RenderNode(
                    node_type=RenderNodeType.TITLE,
                    props={"level": 3},
                    text=i18n.text(card.title_key),
                ),
                RenderNode(
                    node_type=RenderNodeType.TEXT,
                    text=i18n.text(card.subtitle_key),
                ),
            ]

            rows_total = card.payload.get("rows_total")
            updated_at = card.payload.get("updated_at")
            primary_value = card.payload.get("primary_value")
            quality = card.payload.get("quality")

            if primary_value is not None:
                card_children.append(
                    RenderNode(
                        node_type=RenderNodeType.TEXT,
                        props={"class": "mc-v2-kpi-value", "data-field": "primary_value"},
                        text=str(primary_value),
                    )
                )

            if quality:
                card_children.append(
                    RenderNode(
                        node_type=RenderNodeType.TEXT,
                        props={"class": "mc-v2-trust-badge", "data-field": "quality"},
                        text=f'{i18n.text("home.profit_factory.quality")}: {quality}',
                    )
                )

            if rows_total is not None:
                card_children.append(
                    RenderNode(
                        node_type=RenderNodeType.TEXT,
                        props={
                            "class": "mc-v2-card-detail",
                            "data-field": "rows_total",
                        },
                        text=(
                            f'{i18n.text("home.card.status.rows")}: '
                            f"{rows_total}"
                        ),
                    )
                )

            if updated_at:
                card_children.append(
                    RenderNode(
                        node_type=RenderNodeType.TEXT,
                        props={
                            "class": "mc-v2-card-detail",
                            "data-field": "updated_at",
                        },
                        text=(
                            f'{i18n.text("home.card.status.updated")}: '
                            f"{updated_at}"
                        ),
                    )
                )

            if target:
                card_children.append(
                    RenderNode(
                        node_type=RenderNodeType.ACTION,
                        props={
                            "class": "mc-v2-button",
                            "href": target,
                        },
                        text=i18n.text("ui.action.open"),
                    )
                )

            card_nodes.append(
                RenderNode(
                    node_type=RenderNodeType.CARD,
                    props={
                        "class": "mc-v2-card",
                        "data-card": card.card_type.value,
                        "data-status": card.status_code.value,
                    },
                    children=tuple(card_children),
                )
            )

        section_nodes.append(
            RenderNode(
                node_type=RenderNodeType.SECTION,
                props={
                    "class": "mc-v2-section",
                    "data-section": section.section_type.value,
                },
                children=(
                    RenderNode(
                        node_type=RenderNodeType.TITLE,
                        props={"level": 2},
                        text=i18n.text(section.title_key),
                    ),
                    RenderNode(
                        node_type=RenderNodeType.SUBTITLE,
                        text=i18n.text(section.subtitle_key),
                    ),
                    RenderNode(
                        node_type=RenderNodeType.GRID,
                        props={"class": "mc-v2-grid"},
                        children=tuple(card_nodes),
                    ),
                ),
            )
        )

    return RenderDocument(
        root=RenderNode(
            node_type=RenderNodeType.WORKSPACE,
            props={"class": "mc-v2-shell"},
            children=(
                RenderNode(
                    node_type=RenderNodeType.PAGE,
                    props={"class": "mc-v2-page"},
                    children=(
                        RenderNode(
                            node_type=RenderNodeType.TITLE,
                            props={"level": 1},
                            text=i18n.text(layout.title_key),
                        ),
                        RenderNode(
                            node_type=RenderNodeType.HEADER,
                            props={"class": "mc-v2-header"},
                            text=i18n.text(layout.subtitle_key),
                        ),
                        *tuple(section_nodes),
                    ),
                ),
            ),
        )
    )
