from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import psycopg2
import psycopg2.extras

from marketcore.presentation.workspace_v2.domain.risk_snapshot_v2 import (
    RiskClusterSnapshotV2, RiskDecisionAggregateV2, RiskPermissionSnapshotV2, RiskSnapshotV2,
)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).astimezone(timezone.utc)


def _freshness(value: datetime | None, now: datetime, maximum_age_seconds: int) -> str:
    if value is None:
        return "UNAVAILABLE"
    return "CURRENT" if 0 <= (now - value).total_seconds() <= maximum_age_seconds else "STALE"


class RiskV2Resolver:
    def resolve(self, *, generated_at: datetime | None = None) -> RiskSnapshotV2:
        now = _utc(generated_at) or datetime.now(timezone.utc)
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT config_json FROM analytics.risk_configuration_v1 WHERE risk_name='DEFAULT' AND enabled=true LIMIT 1")
                config_row = cursor.fetchone()
                if not config_row or "presentation_freshness_seconds" not in config_row["config_json"]:
                    raise RuntimeError("RISK_PRESENTATION_FRESHNESS_CONFIG_REQUIRED")
                maximum_age = int(config_row["config_json"]["presentation_freshness_seconds"])
                if maximum_age <= 0:
                    raise RuntimeError("RISK_PRESENTATION_FRESHNESS_CONFIG_INVALID")

                cursor.execute("SELECT cluster_name,total_positions,total_heat,portfolio_share,risk_state,calculated_at FROM public.portfolio_risk_state ORDER BY cluster_name")
                cluster_rows = cursor.fetchall()
                cursor.execute("SELECT runtime_allowed,execution_allowed,micro_live_allowed,daily_risk_pct,refreshed_at FROM marketcore_ui.risk_summary_v1 WHERE id=1")
                permission_row = cursor.fetchone()
                cursor.execute("""SELECT count(*) decisions_total,count(*) FILTER (WHERE risk_decision_code='RISK_BLOCK') blocked_total,avg(risk_score) average_risk_score,avg(position_risk_score) average_position_score,avg(exposure_risk_score) average_exposure_score,avg(daily_loss_risk_score) average_daily_loss_score,avg(correlation_risk_score) average_correlation_score,max(refreshed_at) refreshed_at FROM analytics.risk_decision_snapshot_v1""")
                decision_row = cursor.fetchone()

        clusters = tuple(RiskClusterSnapshotV2(str(row["cluster_name"]), int(row["total_positions"]), Decimal(row["total_heat"]), Decimal(row["portfolio_share"]), str(row["risk_state"]), _utc(row["calculated_at"])) for row in cluster_rows)
        permissions = None if permission_row is None else RiskPermissionSnapshotV2(bool(permission_row["runtime_allowed"]), bool(permission_row["execution_allowed"]), bool(permission_row["micro_live_allowed"]), Decimal(permission_row["daily_risk_pct"]) / Decimal(100), _utc(permission_row["refreshed_at"]))
        decisions = RiskDecisionAggregateV2(int(decision_row["decisions_total"]), int(decision_row["blocked_total"]), *[Decimal(decision_row[key]) if decision_row[key] is not None else None for key in ("average_risk_score","average_position_score","average_exposure_score","average_daily_loss_score","average_correlation_score")], _utc(decision_row["refreshed_at"]))
        portfolio_time = max((item.calculated_at for item in clusters), default=None)
        return RiskSnapshotV2(clusters, permissions, decisions, maximum_age, now, _freshness(portfolio_time, now, maximum_age), _freshness(permissions.refreshed_at if permissions else None, now, maximum_age), _freshness(decisions.refreshed_at, now, maximum_age))
