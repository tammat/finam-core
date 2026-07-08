CREATE TABLE IF NOT EXISTS analytics.max_edge_score_audit_v1
(
    audit_id            BIGSERIAL PRIMARY KEY,

    audit_ts            timestamptz NOT NULL DEFAULT now(),

    candidate_id        text NOT NULL,

    symbol              text NOT NULL,

    strategy_code       text NOT NULL,

    timeframe           text NOT NULL,

    edge_score          numeric(20,6) NOT NULL,

    confidence          numeric(20,6) NOT NULL,

    overall_verdict     text NOT NULL,

    source_version      text NOT NULL DEFAULT 'MAX_EDGE_SCORE_AUDIT_V1',

    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.max_edge_score_component_v1
(
    component_id        BIGSERIAL PRIMARY KEY,

    audit_id            bigint
                        REFERENCES analytics.max_edge_score_audit_v1(audit_id)
                        ON DELETE CASCADE,

    component_code      text NOT NULL,

    component_value     numeric(20,6) NOT NULL,

    contribution_score  numeric(20,6) NOT NULL,

    contribution_pct    numeric(20,6) NOT NULL,

    source_column       text NOT NULL,

    source_version      text NOT NULL DEFAULT 'MAX_EDGE_SCORE_AUDIT_V1'
);

CREATE INDEX IF NOT EXISTS
idx_max_edge_score_component_audit
ON analytics.max_edge_score_component_v1(audit_id);

INSERT INTO presentation.ui_resource_v1
(resource_key,
 locale_code,
 caption,
 caption_short,
 caption_mobile,
 tooltip,
 icon,
 resource_group)

VALUES

('max.edge.audit.title',
'ru',
'Аудит Edge Score',
'Audit',
'Audit',
'Расшифровка расчета Edge Score',
'🔎',
'max_edge'),

('max.edge.audit.component',
'ru',
'Компонент',
'Comp',
'Comp',
'Компонент формулы',
'',
'max_edge'),

('max.edge.audit.value',
'ru',
'Значение',
'Value',
'Val',
'Исходное значение',
'',
'max_edge'),

('max.edge.audit.score',
'ru',
'Вклад',
'Score',
'Score',
'Вклад в итоговый Edge Score',
'',
'max_edge'),

('max.edge.audit.percent',
'ru',
'Доля',
'%',
'%',
'Процентный вклад',
'',
'max_edge')

ON CONFLICT(resource_key,locale_code)

DO UPDATE

SET

caption=excluded.caption,
caption_short=excluded.caption_short,
caption_mobile=excluded.caption_mobile,
tooltip=excluded.tooltip,
updated_at=now();

CREATE TABLE IF NOT EXISTS analytics.max_edge_score_audit_metric_v1
(
    metric_id       BIGSERIAL PRIMARY KEY,
    audit_ts        timestamptz NOT NULL DEFAULT now(),
    metric_code     text NOT NULL,
    metric_value    numeric(20,6) NOT NULL DEFAULT 0,
    verdict         text NOT NULL,
    details         jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_version  text NOT NULL DEFAULT 'MAX_EDGE_SCORE_AUDIT_V1',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_max_edge_score_audit_metric_ts
ON analytics.max_edge_score_audit_metric_v1(audit_ts DESC, metric_code);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('max.edge.audit.correlation','ru','Корреляция','Corr','Corr','Связь Edge Score с результатами','','max_edge'),
('max.edge.audit.outlier','ru','Выбросы','Outlier','Out','Аномальные значения score','','max_edge'),
('max.edge.audit.sample_bias','ru','Sample Bias','Sample','Sample','Завышение score при малом числе сделок','','max_edge'),
('max.edge.audit.overall','ru','Итог аудита','Overall','Итог','Общий вывод по качеству Edge Score','','max_edge')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();
