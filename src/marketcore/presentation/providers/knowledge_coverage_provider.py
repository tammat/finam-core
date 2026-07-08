from __future__ import annotations

from decimal import Decimal

import psycopg2
import psycopg2.extras

from marketcore.presentation.widgets.contracts import WidgetViewModel


class KnowledgeCoverageProvider:
    def load(self) -> WidgetViewModel:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    WITH stats AS (
                        SELECT
                            count(*) AS total,
                            sum((regime_code<>'UNKNOWN')::int) AS regime,
                            sum((volatility_state<>'UNKNOWN')::int) AS volatility,
                            sum((liquidity_state<>'UNKNOWN')::int) AS liquidity,
                            sum((volume_state<>'UNKNOWN')::int) AS volume,
                            sum((spread_state<>'UNKNOWN')::int) AS spread,
                            sum((session_state<>'UNKNOWN')::int) AS session,
                            sum((correlation_state<>'UNKNOWN')::int) AS correlation,
                            sum((sector_strength_state<>'UNKNOWN')::int) AS sector
                        FROM knowledge.market_context_v1
                        WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
                    )
                    SELECT
                        total,
                        round(100.0 * (
                            regime + volatility + liquidity + volume + spread + session + correlation + sector
                        ) / nullif(total * 8, 0), 2) AS total_pct,
                        round(100.0 * regime / nullif(total,0), 2) AS regime_pct,
                        round(100.0 * volatility / nullif(total,0), 2) AS volatility_pct,
                        round(100.0 * liquidity / nullif(total,0), 2) AS liquidity_pct,
                        round(100.0 * volume / nullif(total,0), 2) AS volume_pct,
                        round(100.0 * spread / nullif(total,0), 2) AS spread_pct,
                        round(100.0 * session / nullif(total,0), 2) AS session_pct,
                        round(100.0 * correlation / nullif(total,0), 2) AS correlation_pct,
                        round(100.0 * sector / nullif(total,0), 2) AS sector_pct
                    FROM stats
                """)
                row = cur.fetchone() or {}

        def pct(value) -> str:
            if value is None:
                value = Decimal("0")
            return f"{Decimal(str(value)).quantize(Decimal('0.01'))}%"

        return WidgetViewModel(
            widget_id="knowledge_coverage",
            title_key="widget.knowledge_coverage.title",
            icon="🧠",
            priority=35,
            category="knowledge",
            state="readonly",
            content={
                "knowledge.coverage.total": pct(row.get("total_pct")),
                "knowledge.coverage.regime": pct(row.get("regime_pct")),
                "knowledge.coverage.volatility": pct(row.get("volatility_pct")),
                "knowledge.coverage.liquidity": pct(row.get("liquidity_pct")),
                "knowledge.coverage.volume": pct(row.get("volume_pct")),
                "knowledge.coverage.spread": pct(row.get("spread_pct")),
                "knowledge.coverage.session": pct(row.get("session_pct")),
                "knowledge.coverage.correlation": pct(row.get("correlation_pct")),
                "knowledge.coverage.sector_strength": pct(row.get("sector_pct")),
            },
        )
