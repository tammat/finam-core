CREATE TABLE IF NOT EXISTS knowledge.platform_parameter_v1 (
    parameter_id          BIGSERIAL PRIMARY KEY,

    parameter_code        TEXT NOT NULL UNIQUE,
    parameter_name        TEXT NOT NULL,
    parameter_group       TEXT NOT NULL,

    parameter_type        TEXT NOT NULL
                           CHECK (parameter_type IN
                           ('INTEGER','NUMERIC','BOOLEAN','TEXT')),

    parameter_value       TEXT NOT NULL,

    description           TEXT,

    enabled               BOOLEAN NOT NULL DEFAULT TRUE,

    effective_from        TIMESTAMPTZ NOT NULL DEFAULT now(),
    effective_to          TIMESTAMPTZ,

    parameter_version     INTEGER NOT NULL DEFAULT 1,

    source_version        TEXT NOT NULL,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_parameter_group_v1
ON knowledge.platform_parameter_v1(parameter_group, enabled);

CREATE INDEX IF NOT EXISTS idx_platform_parameter_code_v1
ON knowledge.platform_parameter_v1(parameter_code);
