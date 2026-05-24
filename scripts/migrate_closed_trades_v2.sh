#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
ALTER TABLE public.closed_trades
ADD COLUMN IF NOT EXISTS root_symbol TEXT;

ALTER TABLE public.closed_trades
ADD COLUMN IF NOT EXISTS entry_regime TEXT DEFAULT 'unknown';

ALTER TABLE public.closed_trades
ADD COLUMN IF NOT EXISTS exit_regime TEXT DEFAULT 'unknown';

ALTER TABLE public.closed_trades
ADD COLUMN IF NOT EXISTS mae NUMERIC(20,8) DEFAULT 0;

ALTER TABLE public.closed_trades
ADD COLUMN IF NOT EXISTS mfe NUMERIC(20,8) DEFAULT 0;

ALTER TABLE public.closed_trades
ADD COLUMN IF NOT EXISTS realized_rr NUMERIC(20,8) DEFAULT 0;

ALTER TABLE public.closed_trades
ADD COLUMN IF NOT EXISTS quality_score NUMERIC(20,8) DEFAULT 0;

UPDATE public.closed_trades
SET root_symbol =
    CASE
        WHEN symbol LIKE 'NG%@RTSX' THEN 'NG'
        WHEN symbol LIKE 'BR%@RTSX' THEN 'BR'
        WHEN symbol LIKE 'USDRUB%@RTSX' THEN 'USDRUB'
        ELSE symbol
    END
WHERE root_symbol IS NULL;

CREATE INDEX IF NOT EXISTS idx_closed_trades_root_strategy
ON public.closed_trades(root_symbol, strategy, timeframe);

CREATE INDEX IF NOT EXISTS idx_closed_trades_quality
ON public.closed_trades(root_symbol, strategy, timeframe, quality_score DESC);

CREATE OR REPLACE VIEW closed_trade_quality_stats AS
SELECT
    root_symbol,
    symbol,
    strategy,
    timeframe,
    side,
    COUNT(*) AS trades,
    ROUND(SUM(net_pnl)::numeric, 6) AS net_pnl,
    ROUND(AVG(net_pnl)::numeric, 6) AS avg_net_pnl,
    ROUND(AVG(mae)::numeric, 6) AS avg_mae,
    ROUND(AVG(mfe)::numeric, 6) AS avg_mfe,
    ROUND(AVG(realized_rr)::numeric, 6) AS avg_realized_rr,
    ROUND(AVG(quality_score)::numeric, 6) AS avg_quality_score,
    ROUND(
        (COUNT(*) FILTER (WHERE net_pnl > 0)::numeric / NULLIF(COUNT(*), 0)),
        6
    ) AS win_rate,
    ROUND(AVG(holding_seconds)::numeric, 0) AS avg_holding_sec
FROM public.closed_trades
WHERE strategy <> 'unknown'
GROUP BY root_symbol, symbol, strategy, timeframe, side;

GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLE public.closed_trades TO finam;
GRANT SELECT ON public.closed_trade_quality_stats TO finam;
GRANT USAGE, SELECT ON SEQUENCE public.closed_trades_id_seq TO finam;
SQL

echo "CLOSED_TRADES_V2_MIGRATION_OK"
