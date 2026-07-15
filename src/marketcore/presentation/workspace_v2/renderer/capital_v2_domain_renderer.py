from __future__ import annotations

from datetime import datetime, timezone

from marketcore.presentation.render_tree.v2 import RenderContentV2, RenderDocumentV2, RenderNodeStateV2, RenderNodeTypeV2, RenderNodeV2, validate_render_document_v2
from marketcore.presentation.workspace_v2.domain.portfolio_model_v1 import PortfolioSnapshotV1


def _metric(code: str, value: object, format_code: str, *, available: bool = True) -> RenderNodeV2:
    value_node = RenderNodeV2(
        RenderNodeTypeV2.METRIC_VALUE,
        f"capital.{code}.value",
        content=(RenderContentV2(value=value, format_code=format_code) if available else RenderContentV2(message_key="capital.value.unavailable")),
        state=RenderNodeStateV2(availability_code="AVAILABLE" if available else "UNAVAILABLE"),
    )
    return RenderNodeV2(
        RenderNodeTypeV2.METRIC_ROW,
        f"capital.{code}",
        children=(
            RenderNodeV2(RenderNodeTypeV2.METRIC_LABEL, f"capital.{code}.label", content=RenderContentV2(message_key=f"capital.metric.{code}")),
            value_node,
        ),
    )


def render_capital_domain_v2(snapshot: PortfolioSnapshotV1, *, timezone_code: str = "Europe/Moscow", generated_at: datetime | None = None) -> RenderDocumentV2:
    now = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    summary = snapshot.summary[0].values if snapshot.summary else {}
    source_time = summary.get("Время")
    if isinstance(source_time, datetime):
        source_time = (source_time.replace(tzinfo=timezone.utc) if source_time.tzinfo is None else source_time).astimezone(timezone.utc)
    else:
        source_time = now
    has_summary = bool(summary)
    metrics = (
        _metric("equity", summary.get("Стоимость портфеля"), "MONEY_RUB", available="Стоимость портфеля" in summary),
        _metric("total_pnl", summary.get("P&L общий"), "MONEY_RUB", available="P&L общий" in summary),
        _metric("daily_pnl", summary.get("P&L за день"), "MONEY_RUB", available="P&L за день" in summary),
        _metric("positions", summary.get("Позиций"), "INTEGER", available="Позиций" in summary),
        _metric("available", None, "MONEY_RUB", available=False),
    )
    document = RenderDocumentV2(
        document_id="operator.capital.v2", locale_code="ru-RU", fallback_locale_code="ru-RU",
        timezone_code=timezone_code, generated_at=now, source_as_of=source_time,
        quality_code="VERIFIED" if has_summary else "EMPTY",
        root=RenderNodeV2(RenderNodeTypeV2.WORKSPACE, "workspace.capital", children=(
            RenderNodeV2(RenderNodeTypeV2.PAGE, "page.capital", state=RenderNodeStateV2(
                status_code="READY" if has_summary else "EMPTY", quality_code="VERIFIED" if has_summary else "EMPTY",
                freshness_code="AS_OF_REPORTED" if has_summary else "AS_OF_UNAVAILABLE", source_as_of=source_time,
                source_identity="public.v_real_portfolio_summary_ru",
            ), children=(
                RenderNodeV2(RenderNodeTypeV2.TITLE, "capital.title", content=RenderContentV2(message_key="capital.workspace.title", level_code="PAGE")),
                RenderNodeV2(RenderNodeTypeV2.SUBTITLE, "capital.subtitle", content=RenderContentV2(message_key="capital.workspace.subtitle")),
                RenderNodeV2(RenderNodeTypeV2.METRIC_LIST, "capital.metrics", children=metrics),
            )),
        )),
    )
    validate_render_document_v2(document)
    return document
