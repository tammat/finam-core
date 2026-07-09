INSERT INTO presentation.workspace_v2_display_term_v1
(term_code, caption_full, caption_short, caption_mobile, tooltip, enabled, source_version)
VALUES
('PROFIT_FACTOR', 'Коэффициент прибыльности', 'Коэфф. приб.', 'Коэфф.', 'Profit Factor: отношение прибыли к убыткам', TRUE, 'MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1'),
('EXPECTANCY_R', 'Ожидание в R', 'Ожид.', 'Ожид.', 'Математическое ожидание результата в R', TRUE, 'MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1'),
('FEEDBACK_QUEUE', 'Очередь рекомендаций', 'Реком.', 'Реком.', 'Рекомендации системы без автоматического применения', TRUE, 'MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1'),
('MODE', 'Режим работы', 'Режим', 'Режим', 'Текущий режим работы системы', TRUE, 'MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1'),
('PAPER_MODE', 'Бумажная проверка', 'Бумага', 'Бумага', 'Режим без реальных заявок', TRUE, 'MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1'),
('STATUS_WARNING', 'Требует внимания', 'Внимание', 'Вним.', 'Есть ограничения или недостаточно данных', TRUE, 'MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1'),
('STATUS_LOCKED', 'Заблокировано', 'Заблок.', 'Блок.', 'Действие или переход заблокированы', TRUE, 'MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1'),
('STATUS_PASS', 'Пройдено', 'Пройдено', 'ОК', 'Проверка пройдена', TRUE, 'MARKETCORE_WORKSPACE_V2_DISPLAY_TERMS_PATCH_V1')
ON CONFLICT(term_code)
DO UPDATE SET
  caption_full=EXCLUDED.caption_full,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();
