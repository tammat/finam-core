INSERT INTO knowledge.market_v1
(market_code, market_name, description, source_version)
VALUES
('RU_MARKET', 'Российский рынок', 'Рынок российских финансовых инструментов', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1')
ON CONFLICT (market_code) DO UPDATE SET
    market_name=EXCLUDED.market_name,
    description=EXCLUDED.description,
    updated_at=now(),
    source_version=EXCLUDED.source_version;

INSERT INTO knowledge.exchange_v1
(market_id, exchange_code, exchange_name, timezone, currency, source_version)
SELECT market_id, 'MOEX', 'Московская биржа', 'Europe/Moscow', 'RUB', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'
FROM knowledge.market_v1
WHERE market_code='RU_MARKET'
ON CONFLICT (exchange_code) DO UPDATE SET
    exchange_name=EXCLUDED.exchange_name,
    timezone=EXCLUDED.timezone,
    currency=EXCLUDED.currency,
    updated_at=now(),
    source_version=EXCLUDED.source_version;

INSERT INTO knowledge.asset_class_v1
(asset_class_code, asset_class_name, description, source_version)
VALUES
('EQUITY', 'Акции', 'Долевые ценные бумаги', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('FUTURES', 'Фьючерсы', 'Срочные контракты', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('FX', 'Валюта', 'Валютные инструменты', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('BOND', 'Облигации', 'Долговые инструменты', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('COMMODITY', 'Сырьевые инструменты', 'Сырьевые и товарные инструменты', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('INDEX', 'Индексы', 'Индексные инструменты', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1')
ON CONFLICT (asset_class_code) DO UPDATE SET
    asset_class_name=EXCLUDED.asset_class_name,
    description=EXCLUDED.description,
    updated_at=now(),
    source_version=EXCLUDED.source_version;

INSERT INTO knowledge.sector_v1
(sector_code, sector_name, description, source_version)
VALUES
('BANKS', 'Банки', 'Банковский сектор', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('OIL_GAS', 'Нефть и газ', 'Нефтегазовый сектор', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('METALS', 'Металлы', 'Металлургия и добыча', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('TECH', 'Технологии', 'Технологический сектор', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('CONSUMER', 'Потребительский сектор', 'Потребительские компании', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('TRANSPORT', 'Транспорт', 'Транспорт и логистика', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('UTILITIES', 'Инфраструктура', 'Коммунальная и инфраструктурная отрасль', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('UNKNOWN', 'Не классифицировано', 'Сектор требует классификации', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1')
ON CONFLICT (sector_code) DO UPDATE SET
    sector_name=EXCLUDED.sector_name,
    description=EXCLUDED.description,
    updated_at=now(),
    source_version=EXCLUDED.source_version;

INSERT INTO knowledge.market_regime_v1
(regime_code, regime_name, regime_group, description, source_version)
VALUES
('TREND_UP', 'Восходящий тренд', 'TREND', 'Устойчивое восходящее движение', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('TREND_DOWN', 'Нисходящий тренд', 'TREND', 'Устойчивое нисходящее движение', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('RANGE', 'Боковой рынок', 'RANGE', 'Движение в диапазоне', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('HIGH_VOLATILITY', 'Высокая волатильность', 'VOLATILITY', 'Повышенная изменчивость цены', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('LOW_VOLATILITY', 'Низкая волатильность', 'VOLATILITY', 'Пониженная изменчивость цены', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('LOW_LIQUIDITY', 'Низкая ликвидность', 'LIQUIDITY', 'Недостаточная рыночная ликвидность', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('NEWS', 'Новостной режим', 'EVENT', 'Режим влияния существенных новостей', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('HOLIDAY', 'Праздничный режим', 'CALENDAR', 'Нестандартная торговая активность из-за календаря', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('GAP', 'Разрыв цены', 'PRICE_ACTION', 'Существенный ценовой разрыв', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('ABNORMAL', 'Аномальный режим', 'RISK', 'Нетипичное рыночное состояние', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1'),
('UNKNOWN', 'Не определено', 'UNKNOWN', 'Режим еще не классифицирован', 'MARKETCORE_MARKET_KNOWLEDGE_DICTIONARY_SEED_V1')
ON CONFLICT (regime_code) DO UPDATE SET
    regime_name=EXCLUDED.regime_name,
    regime_group=EXCLUDED.regime_group,
    description=EXCLUDED.description,
    updated_at=now(),
    source_version=EXCLUDED.source_version;
