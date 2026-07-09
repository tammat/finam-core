CREATE SCHEMA IF NOT EXISTS presentation;

CREATE TABLE IF NOT EXISTS presentation.ui_theme_v1
(
    theme_code          text PRIMARY KEY,
    theme_name_key      text NOT NULL,
    description_key     text NOT NULL,
    enabled             boolean NOT NULL DEFAULT true,
    is_default          boolean NOT NULL DEFAULT false,
    source_version      text NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS presentation.ui_theme_property_v1
(
    theme_code          text NOT NULL REFERENCES presentation.ui_theme_v1(theme_code),
    property_code       text NOT NULL,
    property_value      text NOT NULL,
    property_type       text NOT NULL,
    description_key     text NOT NULL,
    display_order       integer NOT NULL DEFAULT 100,
    source_version      text NOT NULL,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY(theme_code, property_code)
);

CREATE INDEX IF NOT EXISTS idx_ui_theme_property_v1
ON presentation.ui_theme_property_v1
(
    theme_code,
    display_order
);
