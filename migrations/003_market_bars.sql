-- 003_market_bars.sql
-- OHLCV бары (исторические и intraday)

CREATE TABLE IF NOT EXISTS market_bars (
  symbol        TEXT        NOT NULL,
  timeframe     TEXT        NOT NULL,          -- например: M1, M5, H1, D, W, MN, QR
  ts            TIMESTAMPTZ NOT NULL,          -- время бара (UTC)
  open          DOUBLE PRECISION NOT NULL,
  high          DOUBLE PRECISION NOT NULL,
  low           DOUBLE PRECISION NOT NULL,
  close         DOUBLE PRECISION NOT NULL,
  volume        DOUBLE PRECISION NOT NULL,
  source        TEXT        NOT NULL DEFAULT 'FINAM',  -- источник
  ingested_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),    -- когда записали
  PRIMARY KEY (symbol, timeframe, ts)
);

-- Ускоряет выборку последних баров/интервалов
CREATE INDEX IF NOT EXISTS ix_market_bars_symbol_tf_ts
  ON market_bars (symbol, timeframe, ts DESC);

-- Иногда удобно фильтровать по времени без symbol
CREATE INDEX IF NOT EXISTS ix_market_bars_ts
  ON market_bars (ts DESC);
