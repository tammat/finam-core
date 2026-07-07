CREATE TABLE IF NOT EXISTS analytics.recommendation_feedback_v1 (
    id BIGSERIAL PRIMARY KEY,
    feedback_ts TIMESTAMPTZ NOT NULL DEFAULT now(),

    recommendation_code TEXT NOT NULL,
    target_metric TEXT NOT NULL,

    baseline_value NUMERIC(20,6) NOT NULL DEFAULT 0,
    current_value NUMERIC(20,6) NOT NULL DEFAULT 0,
    delta_value NUMERIC(20,6) NOT NULL DEFAULT 0,

    improved BOOLEAN NOT NULL DEFAULT false,
    confidence NUMERIC(12,6) NOT NULL DEFAULT 0,
    decision_outcome TEXT NOT NULL DEFAULT 'NO_EFFECT',

    status TEXT NOT NULL DEFAULT 'ACTIVE',
    source_version TEXT NOT NULL DEFAULT 'RECOMMENDATION_FEEDBACK_ENGINE_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_ts_v1
ON analytics.recommendation_feedback_v1(feedback_ts DESC);

CREATE INDEX IF NOT EXISTS idx_recommendation_feedback_code_v1
ON analytics.recommendation_feedback_v1(recommendation_code, target_metric);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('recommendation.feedback.title','ru','Обратная связь рекомендаций','Feedback','FB','Оценка полезности рекомендаций','🔁','recommendation'),
('recommendation.feedback.score','ru','Оценка рекомендации','Score','Score','Расчётная уверенность в полезности рекомендации','','recommendation'),
('recommendation.feedback.delta','ru','Изменение метрики','Delta','Δ','Разница между текущим и базовым значением','','recommendation'),
('recommendation.feedback.improved','ru','Улучшение','Improved','OK','Метрика улучшилась после рекомендации','','recommendation'),
('recommendation.feedback.status','ru','Статус','Status','Стат.','Статус оценки рекомендации','','recommendation'),
('recommendation.feedback.outcome','ru','Результат решения','Outcome','Итог','SUCCESS / PARTIAL_SUCCESS / NO_EFFECT / NEGATIVE_EFFECT','','recommendation')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    resource_group=EXCLUDED.resource_group,
    updated_at=now();

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.recommendation_feedback_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
