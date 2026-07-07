CREATE TABLE IF NOT EXISTS analytics.max_edge_ranking_v1 (
    id BIGSERIAL PRIMARY KEY,
    ranking_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    rank_no INTEGER NOT NULL,
    candidate_id TEXT NOT NULL DEFAULT '',
    symbol TEXT NOT NULL DEFAULT '',
    strategy_code TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    confidence NUMERIC(12,6) NOT NULL DEFAULT 0,
    expectancy NUMERIC(20,6) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(20,6) NOT NULL DEFAULT 0,
    net_after_tax NUMERIC(20,6) NOT NULL DEFAULT 0,
    max_drawdown NUMERIC(20,6) NOT NULL DEFAULT 0,
    trades INTEGER NOT NULL DEFAULT 0,
    recommendation_code TEXT NOT NULL DEFAULT 'NO_ACTION',
    source_table TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    source_version TEXT NOT NULL DEFAULT 'MAX_EDGE_DISCOVERY_ENGINE_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_max_edge_ranking_v1_ts
ON analytics.max_edge_ranking_v1(ranking_ts DESC, rank_no);

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('max.edge.title','ru','Максимальный edge','Max Edge','Edge','Рейтинг наиболее перспективных edge','🎯','max_edge'),
('max.edge.rank','ru','Ранг','Rank','№','Место в рейтинге','','max_edge'),
('max.edge.score','ru','Edge Score','Score','Score','Итоговая оценка edge','','max_edge'),
('max.edge.confidence','ru','Доверие','Conf','Conf','Уверенность в качестве edge','','max_edge'),
('max.edge.recommendation','ru','Рекомендация','Reco','Reco','Рекомендуемое следующее действие','','max_edge')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();

