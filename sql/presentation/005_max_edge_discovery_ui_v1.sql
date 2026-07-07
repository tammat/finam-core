CREATE SCHEMA IF NOT EXISTS presentation;

INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('max.edge.ui.title','ru','Максимальный edge','Max Edge','Edge','Текущий рейтинг наиболее перспективных edge','🎯','max_edge'),
('max.edge.ui.current','ru','Текущий max edge','Current','Top','Лидер рейтинга max edge','','max_edge'),
('max.edge.ui.ranking','ru','Рейтинг edge','Ranking','Rank','Список edge по итоговой оценке','','max_edge'),
('max.edge.ui.score','ru','Edge Score','Score','Score','Итоговая оценка edge','','max_edge'),
('max.edge.ui.confidence','ru','Доверие','Conf','Conf','Уверенность в качестве edge','','max_edge'),
('max.edge.ui.symbol','ru','Инструмент','Symbol','Sym','Торговый инструмент','','max_edge'),
('max.edge.ui.strategy','ru','Стратегия','Strategy','Strat','Стратегия или семейство стратегии','','max_edge'),
('max.edge.ui.timeframe','ru','Таймфрейм','TF','TF','Рабочий таймфрейм','','max_edge'),
('max.edge.ui.recommendation','ru','Рекомендация','Reco','Reco','Рекомендуемое следующее действие','','max_edge')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();

GRANT USAGE ON SCHEMA presentation TO finam;
GRANT SELECT ON presentation.ui_resource_v1 TO finam;
