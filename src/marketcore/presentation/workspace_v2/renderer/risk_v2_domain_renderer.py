from __future__ import annotations

from marketcore.presentation.render_tree.v2 import (
    RenderContentV2, RenderDocumentV2, RenderNodeStateV2, RenderNodeTypeV2,
    RenderNodeV2, validate_render_document_v2,
)
from marketcore.presentation.workspace_v2.domain.risk_snapshot_v2 import RiskSnapshotV2


def _leaf(node_type, node_id, *, key=None, value=None, format_code=None, level_code=None, column_code=None, state=None):
    return RenderNodeV2(
        node_type, node_id,
        content=RenderContentV2(message_key=key, value=value, format_code=format_code, level_code=level_code, column_code=column_code),
        state=state,
    )


def _metric(code: str, value: object = None, format_code: str | None = None, *, available: bool = True):
    return RenderNodeV2(
        RenderNodeTypeV2.METRIC_ROW, f"risk.metric.{code}",
        children=(
            _leaf(RenderNodeTypeV2.METRIC_LABEL, f"risk.metric.{code}.label", key=f"risk.metric.{code}"),
            _leaf(
                RenderNodeTypeV2.METRIC_VALUE, f"risk.metric.{code}.value",
                key=None if available else "risk.value.unavailable",
                value=value if available else None,
                format_code=format_code if available else None,
                state=RenderNodeStateV2(availability_code="AVAILABLE" if available else "UNAVAILABLE"),
            ),
        ),
    )


def _cluster_table(snapshot: RiskSnapshotV2):
    headers = tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL, f"risk.clusters.header.{code}", key=f"risk.column.{code}", column_code=code)
        for code in ("cluster", "positions", "heat", "portfolio_share", "state")
    )
    rows = tuple(
        RenderNodeV2(
            RenderNodeTypeV2.TABLE_ROW, f"risk.cluster.{index}",
            state=RenderNodeStateV2(
                status_code=item.risk_state_code,
                freshness_code=snapshot.portfolio_freshness_code,
                source_as_of=item.calculated_at,
                source_identity="public.portfolio_risk_state",
            ),
            children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"risk.cluster.{index}.code", value=item.cluster_code, format_code="DOMAIN_CODE", column_code="cluster"),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"risk.cluster.{index}.positions", value=item.total_positions, format_code="INTEGER", column_code="positions"),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"risk.cluster.{index}.heat", value=item.total_heat, format_code="DECIMAL", column_code="heat"),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"risk.cluster.{index}.share", value=item.portfolio_share, format_code="PERCENT_RATIO", column_code="portfolio_share"),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"risk.cluster.{index}.state", value=item.risk_state_code, format_code="DOMAIN_CODE", column_code="state"),
            ),
        )
        for index, item in enumerate(snapshot.clusters, start=1)
    )
    return RenderNodeV2(
        RenderNodeTypeV2.TABLE, "risk.clusters.table",
        children=(
            RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD, "risk.clusters.head", children=(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW, "risk.clusters.header", children=headers),)),
            RenderNodeV2(RenderNodeTypeV2.TABLE_BODY, "risk.clusters.body", children=rows),
        ),
    )


def render_risk_domain_v2(snapshot: RiskSnapshotV2, *, timezone_code: str = "Europe/Moscow") -> RenderDocumentV2:
    timestamps = [item.calculated_at for item in snapshot.clusters]
    if snapshot.permissions:
        timestamps.append(snapshot.permissions.refreshed_at)
    if snapshot.decisions.refreshed_at:
        timestamps.append(snapshot.decisions.refreshed_at)
    source_as_of = min(timestamps) if timestamps else snapshot.generated_at
    permissions = snapshot.permissions
    metrics = (
        _metric("runtime_allowed", permissions.runtime_allowed, "BOOLEAN", available=permissions is not None),
        _metric("execution_allowed", permissions.execution_allowed, "BOOLEAN", available=permissions is not None),
        _metric("micro_live_allowed", permissions.micro_live_allowed, "BOOLEAN", available=permissions is not None),
        _metric("daily_risk", permissions.daily_risk_ratio, "PERCENT_RATIO", available=permissions is not None),
        _metric("decisions_total", snapshot.decisions.decisions_total, "INTEGER"),
        _metric("decisions_blocked", snapshot.decisions.blocked_total, "INTEGER"),
        _metric("risk_score", snapshot.decisions.average_risk_score, "DECIMAL", available=snapshot.decisions.average_risk_score is not None),
        _metric("drawdown", available=False),
        _metric("risk_budget", available=False),
        _metric("available_risk", available=False),
    )
    document = RenderDocumentV2(
        document_id="operator.risk.v2", locale_code="ru-RU", fallback_locale_code="ru-RU",
        timezone_code=timezone_code, generated_at=snapshot.generated_at, source_as_of=source_as_of,
        quality_code="STALE" if "STALE" in {snapshot.portfolio_freshness_code, snapshot.permission_freshness_code, snapshot.decision_freshness_code} else "VERIFIED",
        root=RenderNodeV2(RenderNodeTypeV2.WORKSPACE, "workspace.risk", children=(
            RenderNodeV2(RenderNodeTypeV2.PAGE, "page.risk", state=RenderNodeStateV2(status_code="WARNING", quality_code="STALE", freshness_code="STALE"), children=(
                _leaf(RenderNodeTypeV2.TITLE, "risk.title", key="risk.workspace.title", level_code="PAGE"),
                _leaf(RenderNodeTypeV2.SUBTITLE, "risk.subtitle", key="risk.workspace.subtitle"),
                RenderNodeV2(RenderNodeTypeV2.METRIC_LIST, "risk.metrics", children=metrics),
                _cluster_table(snapshot),
            )),
        )),
    )
    validate_render_document_v2(document)
    return document
