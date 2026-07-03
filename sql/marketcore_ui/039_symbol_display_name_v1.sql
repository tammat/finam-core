BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.symbol_display_name_v1 (
    symbol TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    asset_hint TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'SYMBOL_DISPLAY_NAME_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO marketcore_ui.symbol_display_name_v1(symbol, display_name, asset_hint)
VALUES
('SBER@MISX','Сбербанк','Акции'),
('GAZP@MISX','Газпром','Акции'),
('LKOH@MISX','Лукойл','Акции'),
('PLZL@MISX','Полюс','Акции'),
('VTBR@MISX','ВТБ','Акции'),
('NVTK@MISX','Новатэк','Акции'),
('OZON@MISX','Ozon','Акции'),
('CNYRUB_TOM@MISX','Юань / рубль TOM','Валюта'),
('USDRUBF@RTSX','Фьючерс доллар / рубль','Фьючерс'),
('CNYRUBF@RTSX','Фьючерс юань / рубль','Фьючерс'),
('BRQ6@RTSX','Brent, август 2026','Фьючерс'),
('BRU6@RTSX','Brent, сентябрь 2026','Фьючерс'),
('BRV6@RTSX','Brent, октябрь 2026','Фьючерс'),
('NGN6@RTSX','Газ, июль 2026','Фьючерс'),
('NGQ6@RTSX','Газ, август 2026','Фьючерс'),
('NGU6@RTSX','Газ, сентябрь 2026','Фьючерс'),
('GDU6@RTSX','Золото, сентябрь 2026','Фьючерс'),
('GLU6@RTSX','Золото, сентябрь 2026','Фьючерс'),
('SVU6@RTSX','Серебро, сентябрь 2026','Фьючерс'),
('BTCUSD','Bitcoin / USD','Crypto'),
('ETHUSD','Ethereum / USD','Crypto'),
('IMOEX','Индекс МосБиржи','Индекс')
ON CONFLICT(symbol) DO UPDATE SET
    display_name=EXCLUDED.display_name,
    asset_hint=EXCLUDED.asset_hint,
    refreshed_at=now();

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.symbol_display_name_v1 TO alex;

COMMIT;

SELECT 'SYMBOL_DISPLAY_NAME_SCHEMA_V1_READY' AS verdict;
