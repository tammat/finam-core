CREATE TABLE IF NOT EXISTS persistent_kill_switch (
    id BIGSERIAL PRIMARY KEY,
    scope TEXT NOT NULL DEFAULT 'GLOBAL',
    symbol TEXT,
    active BOOLEAN NOT NULL DEFAULT false,
    reason TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_persistent_kill_switch_scope_symbol
ON persistent_kill_switch(scope, COALESCE(symbol, ''));

CREATE INDEX IF NOT EXISTS idx_persistent_kill_switch_active
ON persistent_kill_switch(active);
