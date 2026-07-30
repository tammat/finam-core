BEGIN;

CREATE TABLE IF NOT EXISTS analytics.legacy_filled_signal_quarantine_v1 (
    quarantined_at timestamptz NOT NULL,
    signal_id text PRIMARY KEY,
    symbol text NOT NULL,
    old_status text NOT NULL,
    old_rejection_reason text,
    created_at timestamptz NOT NULL,
    payload jsonb,
    reason_code text NOT NULL
);

INSERT INTO analytics.legacy_filled_signal_quarantine_v1
SELECT clock_timestamp(),s.signal_id,s.symbol,s.status,s.rejection_reason,
       s.created_at,s.payload,'LEGACY_FILLED_WITHOUT_CANONICAL_TRADE_OR_V5_SCOPE'
FROM signals s
WHERE s.status='FILLED'
  AND NOT EXISTS (SELECT 1 FROM closed_trades c WHERE c.signal_id=s.signal_id)
  AND NOT EXISTS (
      SELECT 1 FROM signal_fills sf
      WHERE sf.signal_id=s.signal_id AND sf.portfolio_scope LIKE 'FRESH_V5%'
  )
ON CONFLICT(signal_id) DO NOTHING;

UPDATE signals s
SET status='ARCHIVED_LEGACY',
    rejection_reason='legacy_filled_without_canonical_trade_quarantined'
FROM analytics.legacy_filled_signal_quarantine_v1 q
WHERE s.signal_id=q.signal_id AND s.status='FILLED';

GRANT SELECT ON analytics.legacy_filled_signal_quarantine_v1 TO alex,finam;

COMMIT;
