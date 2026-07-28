BEGIN;

CREATE TABLE IF NOT EXISTS analytics.paper_scope_runtime_policy_v1 (
    scope_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    allow_scope_bootstrap boolean NOT NULL DEFAULT false,
    reason text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE analytics.paper_scope_runtime_policy_v1 IS
    'Политика накопления изолированных Paper-когорт. Не заменяет риск, режим, издержки и контроль исполнения.';

INSERT INTO analytics.paper_scope_runtime_policy_v1 (
    scope_code, enabled, allow_scope_bootstrap, reason
)
VALUES
    ('FRESH_V5_CONFIRMED_EQUITY', true, true,
     'V5 накапливает собственную статистику; legacy runtime-control V2/V4 не переносится'),
    ('FRESH_V5_CONFIRMED_FUTURES', true, true,
     'V5 накапливает собственную статистику; legacy runtime-control V2/V4 не переносится')
ON CONFLICT (scope_code) DO UPDATE
SET enabled = EXCLUDED.enabled,
    allow_scope_bootstrap = EXCLUDED.allow_scope_bootstrap,
    reason = EXCLUDED.reason,
    updated_at = now();

COMMIT;
