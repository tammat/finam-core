from __future__ import annotations

import json

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.framework.theme_resolver import ThemeResolverV1
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
    theme_code: str = "DEFAULT",
) -> RenderDocument:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    theme = ThemeResolverV1().resolve(theme_code)
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
            ]

            if card.card_type.value != "ACTION":
                card_children.append(
                    RenderNode(
                        node_type=RenderNodeType.TEXT,
                        text=i18n.text(card.subtitle_key),
                    )
                )

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
            if target and section.section_type.value == "OBSERVATION":
                card_props["activation_target"] = target
                card_props["tab_index"] = 0
                card_props["role"] = "button"
                card_props["aria_label"] = i18n.text(card.title_key)
                card_props["progress_label"] = i18n.text("home.decision.progress")
                card_props["progress_complete_label"] = i18n.text("home.decision.progress_complete")
                card_props["confirmation_title"] = i18n.text("home.decision.title")
                card_props["confirmation_label"] = i18n.text("home.decision.confirm")
                card_props["confirmation_options"] = json.dumps([
                    {"value": "open", "label": i18n.text("home.decision.open_section"), "enabled": True},
                    {"value": "observe", "label": i18n.text("home.decision.keep_observing"), "enabled": True},
                ], ensure_ascii=False)
                card_props["style"] = (
                    f"min-height:{int(theme.get('HOME_STATUS_CARD_MIN_HEIGHT'))}px;"
                    f"padding:{int(theme.get('HOME_STATUS_CARD_PADDING'))}px;"
                )
                for child in card_children:
                    if child.props.get("data-field") == "primary_value":
                        child.props["style"] = (
                            f"font-size:{int(theme.get('HOME_STATUS_KPI_FONT_SIZE'))}px;"
                            f"font-weight:{int(theme.get('HOME_STATUS_KPI_FONT_WEIGHT'))};"
                            "line-height:1.25;letter-spacing:0;"
                        )
            elif target:
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
