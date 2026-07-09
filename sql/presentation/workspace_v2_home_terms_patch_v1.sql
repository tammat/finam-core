INSERT INTO presentation.workspace_v2_display_term_v1
(term_code, caption_full, caption_short, caption_mobile, tooltip, enabled, source_version)
VALUES
('WORKSPACE_TITLE','MarketCore Workspace V2','Workspace V2','Workspace','Рабочее место MarketCore',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('HOME','Главная','Главная','Главная','Главный рабочий экран',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('PROJECT_STATE','Состояние проекта','Состояние','Сост.','Текущее состояние проекта',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('RESEARCH_STATE','Исследование','Исследование','Исслед.','Проект находится в исследовательском режиме',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('READY_STATE','Готово','Готово','Готово','Система готова к следующему этапу',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('NEXT_ACTION','Следующее действие','Далее','Далее','Рекомендуемый следующий шаг',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('CONTINUE_PAPER','Продолжать бумажную проверку','Продолжать бумагу','Бумага','Продолжить накопление Paper-статистики',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('CHECK_APPROVAL','Проверить допуск','Проверить допуск','Допуск','Проверить возможность перехода к следующему режиму',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('MAIN_REASONS','Главные причины','Причины','Причины','Основные причины ограничений',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('TRADES','Сделки','Сделки','Сд.','Количество сделок',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('PORTFOLIO','Портфель','Портфель','Портф.','Капитал, позиции, риск и PnL',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('INSTRUMENTS','Инструменты','Инструменты','Инстр.','Поиск и добавление новых инструментов',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1'),
('OPEN_ACTION','Открыть','Открыть','Откр.','Перейти к разделу',TRUE,'MARKETCORE_WORKSPACE_V2_HOME_TERMS_PATCH_V1')
ON CONFLICT(term_code)
DO UPDATE SET
  caption_full=EXCLUDED.caption_full,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();
