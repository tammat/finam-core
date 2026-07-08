from __future__ import annotations

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.edge_score_model_v2_explain (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    strategy_code TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    group_code TEXT NOT NULL,
                    group_score NUMERIC(12,6) NOT NULL,
                    group_weight NUMERIC(12,6) NOT NULL,
                    group_contribution NUMERIC(12,6) NOT NULL,
                    edge_score_v2 NUMERIC(12,6) NOT NULL,
                    model_verdict TEXT NOT NULL,
                    source_version TEXT NOT NULL
                );
            """)

            cur.execute("""
                DELETE FROM analytics.edge_score_model_v2_explain
                WHERE source_version=%s;
            """, (SOURCE_VERSION,))

            cur.execute("""
                WITH group_weights AS (
                    SELECT
                        replace(metric_code, 'GROUP_', '') AS group_code,
                        weight AS group_weight
                    FROM analytics.edge_score_weight_v2
                    WHERE metric_group='MODEL_GROUP'
                      AND enabled=true
                      AND model_code='EDGE_SCORE_V2'
                )
                INSERT INTO analytics.edge_score_model_v2_explain
                (
                    symbol, strategy_code, timeframe,
                    group_code, group_score, group_weight, group_contribution,
                    edge_score_v2, model_verdict, source_version
                )
                SELECT
                    m.symbol,
                    m.strategy_code,
                    m.timeframe,
                    w.group_code,
                    CASE w.group_code
                        WHEN 'ECONOMIC' THEN m.economic_score
                        WHEN 'RELIABILITY' THEN m.reliability_score
                        WHEN 'EXECUTION' THEN m.execution_score
                        WHEN 'RISK' THEN m.risk_score
                    END AS group_score,
                    w.group_weight,
                    CASE w.group_code
                        WHEN 'ECONOMIC' THEN m.economic_score * w.group_weight
                        WHEN 'RELIABILITY' THEN m.reliability_score * w.group_weight
                        WHEN 'EXECUTION' THEN m.execution_score * w.group_weight
                        WHEN 'RISK' THEN m.risk_score * w.group_weight
                    END AS group_contribution,
                    m.edge_score_v2,
                    m.model_verdict,
                    %s
                FROM analytics.edge_score_model_v2 m
                JOIN group_weights w
                  ON w.group_code IN ('ECONOMIC','RELIABILITY','EXECUTION','RISK')
                WHERE m.source_version='EDGE_SCORE_MODEL_V2';
            """, (SOURCE_VERSION,))

            cur.execute("""
                INSERT INTO presentation.ui_resource_v1
                (resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
                VALUES
                ('edge.score.explain.title', 'ru', 'Объяснение Edge Score V2', 'Explain', 'Explain', 'Объяснение вклада групп в Edge Score V2', '', 'edge_score'),
                ('edge.score.explain.total', 'ru', 'Итоговый score', 'Total', 'Total', 'Итоговая оценка Edge Score V2', '', 'edge_score'),
                ('edge.score.explain.group', 'ru', 'Группа', 'Group', 'Group', 'Группа факторов модели', '', 'edge_score'),
                ('edge.score.explain.score', 'ru', 'Оценка', 'Score', 'Score', 'Оценка группы', '', 'edge_score'),
                ('edge.score.explain.weight', 'ru', 'Вес', 'Weight', 'Weight', 'Вес группы в модели', '', 'edge_score'),
                ('edge.score.explain.contribution', 'ru', 'Вклад', 'Contribution', 'Contr', 'Вклад группы в итоговый score', '', 'edge_score'),
                ('edge.score.explain.verdict', 'ru', 'Вердикт', 'Verdict', 'Verdict', 'Вердикт модели', '', 'edge_score')
                ON CONFLICT(resource_key, locale_code) DO UPDATE SET
                    caption=EXCLUDED.caption,
                    caption_short=EXCLUDED.caption_short,
                    caption_mobile=EXCLUDED.caption_mobile,
                    tooltip=EXCLUDED.tooltip,
                    icon=EXCLUDED.icon,
                    resource_group=EXCLUDED.resource_group,
                    updated_at=now();
            """)

            cur.execute("""
                SELECT count(*) AS rows_total
                FROM analytics.edge_score_model_v2_explain
                WHERE source_version=%s;
            """, (SOURCE_VERSION,))
            row = cur.fetchone()

            print("=== EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD ===")
            print(f"explain_rows={row['rows_total']}")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")
            print("VERDICT=EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD_READY")


if __name__ == "__main__":
    main()
