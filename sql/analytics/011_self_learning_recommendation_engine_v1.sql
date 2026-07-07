CREATE TABLE IF NOT EXISTS analytics.recommendation_score_v1 (
    id BIGSERIAL PRIMARY KEY,
    score_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    recommendation_code TEXT NOT NULL,
    feedback_rows BIGINT NOT NULL DEFAULT 0,
    success_rows BIGINT NOT NULL DEFAULT 0,
    no_effect_rows BIGINT NOT NULL DEFAULT 0,
    negative_rows BIGINT NOT NULL DEFAULT 0,
    avg_confidence NUMERIC(12,6) NOT NULL DEFAULT 0,
    recommendation_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    decision_status TEXT NOT NULL DEFAULT 'ACTIVE',
    source_version TEXT NOT NULL DEFAULT 'SELF_LEARNING_RECOMMENDATION_ENGINE_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_score_v1_ts
ON analytics.recommendation_score_v1(score_ts DESC);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('recommendation.learning.title','ru','Обучение рекомендаций','Learning','Learn','Оценка качества рекомендаций по фактическому результату','🧠','recommendation'),
('recommendation.learning.score','ru','Итоговый score','Score','Score','Сводная оценка рекомендации','','recommendation'),
('recommendation.learning.status','ru','Решение','Status','Стат.','ACTIVE / REVIEW / STOP','','recommendation')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    resource_group=EXCLUDED.resource_group,
    updated_at=now();

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.recommendation_score_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
