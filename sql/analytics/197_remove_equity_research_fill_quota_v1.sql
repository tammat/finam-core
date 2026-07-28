BEGIN;

-- Общая исследовательская квота 6/6 мешала независимому накоплению V3.
-- Практически снимаем только этот лимит; риск, anti-reentry и OOS gates остаются.
UPDATE analytics.paper_research_quota_policy_v1
SET max_fills = 1000000,
    source_version = 'REMOVE_EQUITY_AGGREGATE_QUOTA_V1',
    updated_at = clock_timestamp()
WHERE policy_code = 'EQUITY_RESEARCH_PAPER_V1';

COMMIT;
