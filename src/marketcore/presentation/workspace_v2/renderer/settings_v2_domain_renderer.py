from __future__ import annotations

from datetime import datetime, timezone

from marketcore.presentation.render_tree.v2 import (
    RenderContentV2,
    RenderDocumentV2,
    RenderNodeStateV2,
    RenderNodeTypeV2,
    RenderNodeV2,
    validate_render_document_v2,
)
from marketcore.presentation.services.operator_settings_v1 import OperatorSettingsV1


def _content(
    node_type: RenderNodeTypeV2,
    node_id: str,
    *,
    message_key: str | None = None,
    value: object = None,
    format_code: str | None = None,
    level_code: str | None = None,
) -> RenderNodeV2:
    return RenderNodeV2(
        node_type=node_type,
        node_id=node_id,
        content=RenderContentV2(
            message_key=message_key,
            value=value,
            format_code=format_code,
            level_code=level_code,
        ),
    )


def _setting_row(code: str, value: str) -> RenderNodeV2:
    return RenderNodeV2(
        node_type=RenderNodeTypeV2.METRIC_ROW,
        node_id=f"settings.{code}",
        children=(
            _content(
                RenderNodeTypeV2.METRIC_LABEL,
                f"settings.{code}.label",
                message_key=f"settings.field.{code}",
            ),
            _content(
                RenderNodeTypeV2.METRIC_VALUE,
                f"settings.{code}.value",
                value=value,
                format_code="DOMAIN_VALUE",
            ),
        ),
    )


def render_settings_domain_v2(
    settings: OperatorSettingsV1,
    *,
    locale_code: str = "ru-RU",
    fallback_locale_code: str = "ru-RU",
    generated_at: datetime | None = None,
) -> RenderDocumentV2:
    now = generated_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    document = RenderDocumentV2(
        document_id="operator.settings.v2",
        locale_code=locale_code,
        fallback_locale_code=fallback_locale_code,
        timezone_code=settings.timezone,
        generated_at=now,
        source_as_of=now,
        quality_code="CONFIGURATION_VALIDATED",
        root=RenderNodeV2(
            node_type=RenderNodeTypeV2.WORKSPACE,
            node_id="workspace.settings",
            children=(
                RenderNodeV2(
                    node_type=RenderNodeTypeV2.PAGE,
                    node_id="page.settings",
                    state=RenderNodeStateV2(
                        status_code="READY",
                        quality_code="CONFIGURATION_VALIDATED",
                        freshness_code="CURRENT",
                        source_as_of=now,
                        source_identity="operator.settings.environment.v1",
                    ),
                    children=(
                        _content(
                            RenderNodeTypeV2.TITLE,
                            "settings.title",
                            message_key="settings.workspace.title",
                            level_code="PAGE",
                        ),
                        _content(
                            RenderNodeTypeV2.SUBTITLE,
                            "settings.subtitle",
                            message_key="settings.workspace.subtitle",
                        ),
                        RenderNodeV2(
                            node_type=RenderNodeTypeV2.METRIC_LIST,
                            node_id="settings.current",
                            children=(
                                _setting_row("timezone", settings.timezone),
                                _setting_row("currency", settings.currency),
                                _setting_row("broker", settings.broker),
                                _setting_row("locale", locale_code),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    validate_render_document_v2(document)
    return document
