from __future__ import annotations

from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
from marketcore.presentation.workspace_v2.viewmodel.home_v2_viewmodel import HomeV2ViewModel


def render_home_v2(vm: HomeV2ViewModel, locale_code: str = "ru") -> RenderDocument:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    layout = vm.layout

    section_nodes = []

    for section in layout.ordered_sections():
        card_nodes = []

        for card in section.ordered_cards():
            target = ""
            if card.actions:
                target = str(card.actions[0].get("target", ""))

            children = [
                RenderNode("h3", text=i18n.text(card.title_key)),
                RenderNode("div", text=i18n.text(card.subtitle_key)),
            ]

            rows_total = card.payload.get("rows_total")
            updated_at = card.payload.get("updated_at")

            if rows_total is not None:
                children.append(
                    RenderNode(
                        "div",
                        text=f'{i18n.text("home.card.status.rows")}: {rows_total}',
                    )
                )

            if updated_at:
                children.append(
                    RenderNode(
                        "div",
                        text=f'{i18n.text("home.card.status.updated")}: {updated_at}',
                    )
                )

            if target:
                children.append(
                    RenderNode(
                        "a",
                        props={
                            "class": "mc-v2-button",
                            "href": target,
                        },
                        text=i18n.text("ui.action.open"),
                    )
                )

            card_nodes.append(
                RenderNode(
                    "article",
                    props={
                        "class": "mc-v2-card",
                        "data-card": card.card_type.value,
                        "data-status": card.status_code.value,
                    },
                    children=tuple(children),
                )
            )

        section_nodes.append(
            RenderNode(
                "section",
                props={
                    "class": "mc-v2-section",
                    "data-section": section.section_type.value,
                },
                children=(
                    RenderNode("h2", text=i18n.text(section.title_key)),
                    RenderNode("p", text=i18n.text(section.subtitle_key)),
                    RenderNode(
                        "div",
                        props={"class": "mc-v2-grid"},
                        children=tuple(card_nodes),
                    ),
                ),
            )
        )

    return RenderDocument(
        root=RenderNode(
            "main",
            props={"class": "mc-v2-shell"},
            children=(
                RenderNode(
                    "section",
                    props={"class": "mc-v2-page"},
                    children=(
                        RenderNode("h1", text=i18n.text(layout.title_key)),
                        RenderNode(
                            "header",
                            props={"class": "mc-v2-header"},
                            text=i18n.text(layout.subtitle_key),
                        ),
                        *tuple(section_nodes),
                    ),
                ),
            ),
        )
    )
