from __future__ import annotations

import json
from typing import Any

from finam_core.orderflow.smart_money_features import SmartMoneyFeatures


class SmartMoneyFeatureRepository:
    """Русский комментарий: сохраняет smart-money признаки в PostgreSQL."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def save(self, features: SmartMoneyFeatures) -> None:
        raw = {
            "symbol": features.symbol,
            "rvol": features.rvol,
            "tick_velocity": features.tick_velocity,
            "price_velocity": features.price_velocity,
            "range_pct": features.range_pct,
            "absorption_score": features.absorption_score,
            "sweep_reclaim_score": features.sweep_reclaim_score,
            "impulse_score": features.impulse_score,
            "smart_money_score": features.smart_money_score,
            "label": features.label,
        }

        sql = """
        insert into smart_money_feature_events (
            symbol,
            rvol,
            tick_velocity,
            price_velocity,
            range_pct,
            absorption_score,
            sweep_reclaim_score,
            impulse_score,
            smart_money_score,
            label,
            raw_json
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        features.symbol,
                        features.rvol,
                        features.tick_velocity,
                        features.price_velocity,
                        features.range_pct,
                        features.absorption_score,
                        features.sweep_reclaim_score,
                        features.impulse_score,
                        features.smart_money_score,
                        features.label,
                        json.dumps(raw, ensure_ascii=False),
                    ),
                )
            conn.commit()
