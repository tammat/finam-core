CREATE SCHEMA IF NOT EXISTS presentation;

CREATE TABLE IF NOT EXISTS presentation.workspace_v2_design_token_v1 (
    token_code TEXT PRIMARY KEY,
    token_group TEXT NOT NULL,
    token_value TEXT NOT NULL,
    token_description TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS presentation.workspace_v2_display_term_v1 (
    term_code TEXT PRIMARY KEY,
    caption_full TEXT NOT NULL,
    caption_short TEXT NOT NULL,
    caption_mobile TEXT NOT NULL,
    tooltip TEXT NOT NULL DEFAULT '',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS presentation.workspace_v2_module_v1 (
    module_code TEXT PRIMARY KEY,
    route_path TEXT NOT NULL,
    caption_full TEXT NOT NULL,
    caption_short TEXT NOT NULL,
    caption_mobile TEXT NOT NULL,
    module_group TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO presentation.workspace_v2_design_token_v1
(token_code, token_group, token_value, token_description, enabled, source_version)
VALUES
('TOUCH_TARGET_MIN', 'SIZE', '44px', 'Минимальный размер touch-элемента', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('CARD_RADIUS', 'RADIUS', '18px', 'Скругление карточек', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('GRID_GAP', 'SPACING', '12px', 'Базовый отступ сетки', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('PHONE_BREAKPOINT', 'BREAKPOINT', '820px', 'Граница мобильного режима', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('STATUS_OK', 'STATUS', 'OK', 'Положительный статус', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('STATUS_WARNING', 'STATUS', 'WARNING', 'Требует внимания', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('STATUS_BLOCKED', 'STATUS', 'BLOCKED', 'Заблокировано', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('STATUS_LOCKED', 'STATUS', 'LOCKED', 'Заблокировано политикой', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1')
ON CONFLICT(token_code)
DO UPDATE SET
  token_group=EXCLUDED.token_group,
  token_value=EXCLUDED.token_value,
  token_description=EXCLUDED.token_description,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO presentation.workspace_v2_display_term_v1
(term_code, caption_full, caption_short, caption_mobile, tooltip, enabled, source_version)
VALUES
('MODEL_HEALTH', 'Здоровье модели', 'Здор. модели', 'Здор. мод.', 'Сводная оценка состояния модели', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('MARKET_MODEL_QUALITY', 'Качество модели рынка', 'Кач. модели', 'Кач. мод.', 'Качество рыночной модели', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('LEARNING_READINESS', 'Готовность к обучению', 'Готовн.', 'Готовн.', 'Готовность к обучению на накопленной статистике', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('ROBUSTNESS', 'Устойчивость модели', 'Устойчив.', 'Устойчив.', 'Защита от переобучения', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('PROFIT_READINESS', 'Готовность к прибыли', 'Готовн. прибыли', 'Гот. приб.', 'Готовность к переходу после Paper', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('PRODUCTION_READINESS', 'Готовность к Production', 'Прод.', 'Прод.', 'Готовность к промышленному режиму', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('CAPITAL', 'Капитал', 'Капитал', 'Капитал', 'Денежные средства и капитал', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('CAPITAL_INPUT', 'Добавление капитала', 'Доб. капитал', 'Доб. кап.', 'Ввод или корректировка капитала с подтверждением', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('INSTRUMENT_SEARCH', 'Поиск инструментов', 'Поиск инстр.', 'Поиск', 'Поиск новых инструментов для исследования', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('INSTRUMENT_ADD', 'Добавление инструментов', 'Доб. инстр.', 'Доб. инстр.', 'Добавление инструментов после проверки', TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1')
ON CONFLICT(term_code)
DO UPDATE SET
  caption_full=EXCLUDED.caption_full,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();

INSERT INTO presentation.workspace_v2_module_v1
(module_code, route_path, caption_full, caption_short, caption_mobile, module_group, priority, enabled, source_version)
VALUES
('MISSION_CONTROL', '/workspace-v2', 'Центр управления', 'Центр', 'Центр', 'MAIN', 10, TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('PORTFOLIO', '/workspace-v2/portfolio', 'Портфель', 'Портфель', 'Портф.', 'MAIN', 20, TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('CAPITAL', '/workspace-v2/capital', 'Капитал', 'Капитал', 'Кап.', 'MAIN', 30, TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('PAPER', '/workspace-v2/paper', 'Бумажная проверка', 'Бумага', 'Бумага', 'VALIDATION', 40, TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('RUNTIME', '/workspace-v2/runtime', 'Runtime', 'Runtime', 'Run', 'OPERATIONS', 50, TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('RESEARCH', '/workspace-v2/research', 'Исследования', 'Research', 'Исслед.', 'RESEARCH', 60, TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('INSTRUMENTS', '/workspace-v2/instruments', 'Поиск и добавление инструментов', 'Инструменты', 'Инстр.', 'RESEARCH', 70, TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1'),
('SETTINGS', '/workspace-v2/settings', 'Настройки', 'Настройки', 'Настр.', 'ADMIN', 100, TRUE, 'MARKETCORE_WORKSPACE_V2_DESIGN_SYSTEM_V1')
ON CONFLICT(module_code)
DO UPDATE SET
  route_path=EXCLUDED.route_path,
  caption_full=EXCLUDED.caption_full,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  module_group=EXCLUDED.module_group,
  priority=EXCLUDED.priority,
  enabled=EXCLUDED.enabled,
  source_version=EXCLUDED.source_version,
  updated_at=now();
