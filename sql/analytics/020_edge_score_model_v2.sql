CREATE TABLE IF NOT EXISTS analytics.edge_score_weight_v2 (
    metric_code TEXT PRIMARY KEY,
    metric_group TEXT NOT NULL,
    weight NUMERIC(12,6) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'EDGE_SCORE_MODEL_V2',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE analytics.edge_score_weight_v2
ADD COLUMN IF NOT EXISTS model_code TEXT NOT NULL DEFAULT 'EDGE_SCORE_V2';

CREATE UNIQUE INDEX IF NOT EXISTS ux_edge_score_weight_v2_model_metric
ON analytics.edge_score_weight_v2(model_code, metric_code);

CREATE TABLE IF NOT EXISTS analytics.edge_score_model_v2 (
    id BIGSERIAL PRIMARY KEY,
    score_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    candidate_id TEXT NOT NULL DEFAULT '',
    symbol TEXT NOT NULL DEFAULT '',
    strategy_code TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    economic_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    reliability_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    execution_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    risk_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    edge_score_v2 NUMERIC(12,6) NOT NULL DEFAULT 0,
    model_verdict TEXT NOT NULL DEFAULT 'ACTIVE',
    source_version TEXT NOT NULL DEFAULT 'EDGE_SCORE_MODEL_V2',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.edge_score_metric_v2 (
    id BIGSERIAL PRIMARY KEY,
    model_id BIGINT NOT NULL REFERENCES analytics.edge_score_model_v2(id) ON DELETE CASCADE,
    metric_code TEXT NOT NULL,
    raw_value NUMERIC(20,6) NOT NULL DEFAULT 0,
    normalized_value NUMERIC(12,6) NOT NULL DEFAULT 0,
    weight NUMERIC(12,6) NOT NULL DEFAULT 0,
    contribution NUMERIC(12,6) NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL DEFAULT 'EDGE_SCORE_MODEL_V2'
);

INSERT INTO analytics.edge_score_weight_v2(metric_code, metric_group, weight)
VALUES
('NET_AFTER_TAX','ECONOMIC',0.40),
('PROFIT_FACTOR','ECONOMIC',0.30),
('EXPECTANCY','ECONOMIC',0.30),
('TRADES','RELIABILITY',0.70),
('CONFIDENCE','RELIABILITY',0.30),
('EXECUTION_DEFAULT','EXECUTION',1.00),
('MAX_DRAWDOWN','RISK',1.00)
ON CONFLICT(metric_code) DO UPDATE SET
    metric_group=EXCLUDED.metric_group,
    weight=EXCLUDED.weight,
    enabled=true,
    updated_at=now();

INSERT INTO analytics.edge_score_weight_v2(metric_code, metric_group, weight, model_code)
VALUES
('GROUP_ECONOMIC','MODEL_GROUP',0.40,'EDGE_SCORE_V2'),
('GROUP_RELIABILITY','MODEL_GROUP',0.30,'EDGE_SCORE_V2'),
('GROUP_EXECUTION','MODEL_GROUP',0.15,'EDGE_SCORE_V2'),
('GROUP_RISK','MODEL_GROUP',0.15,'EDGE_SCORE_V2')
ON CONFLICT(metric_code) DO UPDATE SET
    metric_group=EXCLUDED.metric_group,
    weight=EXCLUDED.weight,
    model_code=EXCLUDED.model_code,
    enabled=true,
    updated_at=now();


INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('edge.score.v2.title','ru','Модель Edge Score V2','Score V2','V2','Новая объяснимая модель оценки edge','🎯','edge_score'),
('edge.score.v2.economic','ru','Экономика','Economic','Eco','Экономическая оценка','','edge_score'),
('edge.score.v2.reliability','ru','Надёжность','Reliability','Rel','Надёжность выборки','','edge_score'),
('edge.score.v2.execution','ru','Исполнение','Execution','Exec','Оценка исполнимости','','edge_score'),
('edge.score.v2.risk','ru','Риск','Risk','Risk','Оценка риска','','edge_score')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();
