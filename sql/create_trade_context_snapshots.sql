CREATE TABLE IF NOT EXISTS trade_context_snapshots (
    id BIGSERIAL PRIMARY KEY
);

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS trade_id TEXT NOT NULL DEFAULT '';

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS db_trade_id BIGINT;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS run_id TEXT;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS symbol TEXT NOT NULL DEFAULT '';

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS strategy TEXT NOT NULL DEFAULT '';

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS timeframe TEXT NOT NULL DEFAULT '';

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS side TEXT;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS qty DOUBLE PRECISION;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS price DOUBLE PRECISION;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS reason TEXT;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS source TEXT;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS event_type TEXT NOT NULL DEFAULT 'paper_trade';

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS ts TIMESTAMPTZ;

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

ALTER TABLE trade_context_snapshots
ADD COLUMN IF NOT EXISTS snapshot JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS ux_trade_context_snapshots_trade_event
ON trade_context_snapshots(trade_id, event_type);

CREATE INDEX IF NOT EXISTS idx_trade_context_snapshots_symbol_created
ON trade_context_snapshots(symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_trade_context_snapshots_strategy_tf
ON trade_context_snapshots(strategy, timeframe);

CREATE INDEX IF NOT EXISTS idx_trade_context_snapshots_snapshot_gin
ON trade_context_snapshots USING GIN(snapshot);

-- Русский комментарий: snapshot может относиться к paper trade/fill, а не только к closed_trade.
ALTER TABLE trade_context_snapshots
ALTER COLUMN closed_trade_id DROP NOT NULL;

-- Русский комментарий: snapshot paper/fill должен иметь trade_source для совместимости со старой схемой.
ALTER TABLE trade_context_snapshots
ALTER COLUMN trade_source SET DEFAULT 'paper';

UPDATE trade_context_snapshots
SET trade_source = 'paper'
WHERE trade_source IS NULL;

ALTER TABLE trade_context_snapshots
ALTER COLUMN trade_source SET NOT NULL;
