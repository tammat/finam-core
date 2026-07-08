from __future__ import annotations

from decimal import Decimal

import psycopg2
import psycopg2.extras

from marketcore.presentation.viewmodels.recommendation_viewmodel import RecommendationWidgetViewModel
from marketcore.presentation.widgets.contracts import WidgetViewModel


class RecommendationWidgetProvider:
    def load(self) -> WidgetViewModel:
        view_model = self._load_view_model()

        content: dict[str, str] = {
            "recommendation.confidence": view_model.confidence_text,
        }

        for idx, reason_key in enumerate(view_model.reason_keys, start=1):
            content[reason_key] = "✓"

        return WidgetViewModel(
            widget_id=view_model.widget_id,
            title_key=view_model.title_key,
            icon="🧠",
            priority=25,
            category="recommendation",
            state=view_model.state,
            content={
                view_model.recommendation_key: "",
                **content,
            },
        )

    def _load_view_model(self) -> RecommendationWidgetViewModel:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT recommendation_id,
                           recommendation_code,
                           recommendation_confidence
                    FROM knowledge.recommendation_result_v1
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                rec = cur.fetchone()

                if not rec:
                    return RecommendationWidgetViewModel(
                        widget_id="recommendation",
                        title_key="widget.recommendation.title",
                        recommendation_key="recommendation.insufficient_data",
                        confidence_text="0%",
                        reason_keys=["reason.insufficient_data"],
                        state="readonly",
                    )

                cur.execute(
                    """
                    SELECT reason_code
                    FROM knowledge.recommendation_reason_v1
                    WHERE recommendation_id=%s
                    ORDER BY reason_order
                    """,
                    (rec["recommendation_id"],),
                )
                reasons = [str(r["reason_code"]) for r in cur.fetchall()]

        confidence = Decimal(str(rec["recommendation_confidence"] or 0))
        confidence_pct = (confidence * Decimal("100")).quantize(Decimal("0.01"))

        return RecommendationWidgetViewModel(
            widget_id="recommendation",
            title_key="widget.recommendation.title",
            recommendation_key=f"recommendation.{str(rec['recommendation_code']).lower()}",
            confidence_text=f"{confidence_pct}%",
            reason_keys=reasons or ["reason.insufficient_data"],
            state="readonly",
        )
