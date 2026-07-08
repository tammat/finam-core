WITH keepers AS (
  SELECT
    symbol,
    timeframe,
    context_date,
    source_version,
    max(context_id) AS keep_context_id
  FROM knowledge.market_context_v1
  WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
  GROUP BY symbol, timeframe, context_date, source_version
),
duplicate_map AS (
  SELECT
    c.context_id AS old_context_id,
    k.keep_context_id
  FROM knowledge.market_context_v1 c
  JOIN keepers k
    ON k.symbol=c.symbol
   AND k.timeframe=c.timeframe
   AND k.context_date=c.context_date
   AND k.source_version=c.source_version
  WHERE c.source_version='MARKET_CONTEXT_COLLECTOR_V1'
    AND c.context_id <> k.keep_context_id
)
UPDATE knowledge.edge_context_v1 e
SET context_id = d.keep_context_id
FROM duplicate_map d
WHERE e.context_id = d.old_context_id;

DELETE FROM knowledge.market_context_v1 c
USING (
  SELECT
    c.context_id,
    max(c.context_id) OVER (
      PARTITION BY c.symbol, c.timeframe, c.context_date, c.source_version
    ) AS keep_context_id
  FROM knowledge.market_context_v1 c
  WHERE c.source_version='MARKET_CONTEXT_COLLECTOR_V1'
) d
WHERE c.context_id=d.context_id
  AND c.context_id <> d.keep_context_id;

CREATE UNIQUE INDEX IF NOT EXISTS ux_market_context_current_v1
ON knowledge.market_context_v1(symbol, timeframe, context_date, source_version)
WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1';
