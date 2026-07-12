from __future__ import annotations

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.services.datetime_service import DateTimeService
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
    datetime_service = DateTimeService()
    layout = vm.layout

    section_nodes: list[RenderNode] = []

    for section in layout.ordered_sections():
        card_nodes: list[RenderNode] = []

        for card in section.ordered_cards():
            target = ""
            card_class = "mc-v2-card"

            if card.widget_id == "home.card.portfolio":
                card_class += " mc-device-desktop-only"
            elif card.widget_id == "home.card.portfolio.tablet":
                card_class += " mc-device-tablet-only"
            elif card.widget_id == "home.card.portfolio.phone":
                card_class += " mc-device-phone-only"

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
            availability = card.payload.get("availability")

            if availability:
                card_children.append(
                    RenderNode(
                        node_type=RenderNodeType.TEXT,
                        props={
                            "class": "mc-v2-availability",
                            "data-availability": str(availability),
                        },
                        text=("Доступно" if availability == "AVAILABLE" else "Недоступно"),
                    )
                )

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
                            f'{datetime_service.format_datetime(updated_at)}'
                        ),
                    )
                )

            card_props = {
                "class": card_class,
                "data-card": card.card_type.value,
                "data-status": card.status_code.value,
                "data-availability": str(availability or ""),
            }
            if target:
                card_props["href"] = target
                card_props["aria_label"] = i18n.text(card.title_key)

            card_nodes.append(
                RenderNode(
                    node_type=RenderNodeType.CARD,
                    props=card_props,
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
