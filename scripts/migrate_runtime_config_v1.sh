#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS runtime_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'str',
    scope TEXT NOT NULL DEFAULT 'runtime',
    is_secret BOOLEAN NOT NULL DEFAULT false,
    is_production_critical BOOLEAN NOT NULL DEFAULT true,
    description TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO runtime_config (key, value, value_type, scope, is_secret, description)
VALUES
('EXECUTION_MODE', 'paper', 'str', 'execution', false, 'Режим исполнения: paper, real_dry_run, real'),
('REAL_EXECUTION_ENABLED', '0', 'bool', 'execution_safety', false, 'Глобальный разрешатель real execution'),
('REAL_ORDER_CONFIRM', '0', 'bool', 'execution_safety', false, 'Финальное подтверждение отправки real orders'),
('REAL_TRADING_ENABLED', '0', 'bool', 'execution_safety', false, 'Общий флаг реальной торговли'),
('REAL_STOCK_TRADING_ENABLED', '0', 'bool', 'execution_safety', false, 'Разрешение real-торговли акциями'),
('ALLOW_PORTFOLIO_REPAIR', '0', 'bool', 'reconciliation', false, 'Разрешение автоматического ремонта портфеля'),

('DATABASE_URL', '', 'str', 'database', true, 'PostgreSQL DSN'),
('FINAM_TOKEN', '', 'str', 'broker', true, 'Finam token'),
('FINAM_ACCOUNT_ID', '', 'str', 'broker', false, 'Finam account id'),
('FINAM_GRPC_ENDPOINT', 'api.finam.ru:443', 'str', 'broker', false, 'Finam gRPC endpoint'),

('TG_TOKEN', '', 'str', 'telegram', true, 'Telegram bot token'),
('TG_CHAT_ID', '', 'str', 'telegram', false, 'Telegram chat id'),

('MD_DEBUG', '0', 'bool', 'market_data', false, 'Debug logs for market data'),
('MD_WATCHDOG_MODE', 'soft', 'str', 'market_data', false, 'Market data watchdog mode'),
('MD_FIRST_QUOTE_GRACE_SEC', '60', 'float', 'market_data', false, 'Grace period before first quote'),
('MD_RECONNECT_INITIAL_SEC', '0.5', 'float', 'market_data', false, 'Initial reconnect delay'),
('MD_RECONNECT_MAX_SEC', '30.0', 'float', 'market_data', false, 'Maximum reconnect delay'),

('ENABLE_ENGINE_COORDINATOR', '0', 'bool', 'runtime_gate', false, 'Enable EngineCoordinator'),
('ENABLE_ENGINE_COORDINATOR_ON_QUOTE', '0', 'bool', 'runtime_gate', false, 'Enable EngineCoordinator quote path'),
('ENABLE_ENGINE_COORDINATOR_EXECUTION_ROUTE', '0', 'bool', 'runtime_gate', false, 'Enable EngineCoordinator execution route'),

('ENABLE_PAPER_FILLS', '1', 'bool', 'paper', false, 'Enable paper fills'),
('SIMULATE_MARKET', '0', 'bool', 'simulation', false, 'Enable simulated market mode')
ON CONFLICT (key) DO NOTHING;
SQL

echo "RUNTIME_CONFIG_V1_MIGRATION_OK"
