from __future__ import annotations

import json
from typing import Any


class PolicyImpactRepository:
    """Русский комментарий: сохраняет сравнение adaptive risk policy."""

    def __init__(self, conn: Any):
        self.conn = conn

    def save(
        self,
        *,
        report_id: str,
        base: dict,
        limited: dict,
        selective: dict,
    ) -> int:
        payload = {
            "report_id": report_id,
            "base": base,
            "limited": limited,
            "selective": selective,
        }

        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into research_policy_impact_reports (
                    report_id,

                    base_campaign_id,
                    limited_campaign_id,
                    selective_campaign_id,

                    base_trades,
                    limited_trades,
                    selective_trades,

                    base_net_pnl,
                    limited_net_pnl,
                    selective_net_pnl,

                    base_expectancy,
                    limited_expectancy,
                    selective_expectancy,

                    base_winrate,
                    limited_winrate,
                    selective_winrate,

                    raw_json
                )
                values (
                    %s,

                    %s,
                    %s,
                    %s,

                    %s,
                    %s,
                    %s,

                    %s,
                    %s,
                    %s,

                    %s,
                    %s,
                    %s,

                    %s,
                    %s,
                    %s,

                    %s::jsonb
                )
                """,
                (
                    report_id,

                    base["campaign_id"],
                    limited["campaign_id"],
                    selective["campaign_id"],

                    base["trades"],
                    limited["trades"],
                    selective["trades"],

                    base["net_pnl"],
                    limited["net_pnl"],
                    selective["net_pnl"],

                    base["expectancy"],
                    limited["expectancy"],
                    selective["expectancy"],

                    base["winrate"],
                    limited["winrate"],
                    selective["winrate"],

                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )

        self.conn.commit()
        return 1
