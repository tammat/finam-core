CREATE OR REPLACE VIEW v_production_health AS
SELECT
    now() AS checked_at,
    (SELECT COALESCE(max(id), 0) FROM event_store) AS latest_event_id,
    (
        SELECT COALESCE(last_event_id, 0)
        FROM projection_checkpoints
        WHERE name = 'projection_worker'
    ) AS projection_checkpoint_id,
    (
        (SELECT COALESCE(max(id), 0) FROM event_store)
        -
        COALESCE((
            SELECT last_event_id
            FROM projection_checkpoints
            WHERE name = 'projection_worker'
        ), 0)
    ) AS projection_lag,
    (
        SELECT count(*)
        FROM event_dead_letters
        WHERE resolved = false
    ) AS dlq_unresolved,
    (
        SELECT count(*)
        FROM order_projection
    ) AS orders_count,
    (
        SELECT count(*)
        FROM position_projection
    ) AS positions_count,
    (
        SELECT state
        FROM portfolio_projection
        WHERE id = 'GLOBAL'
    ) AS portfolio_state;

CREATE OR REPLACE VIEW v_orders_dashboard AS
SELECT
    order_id,
    state->>'symbol' AS symbol,
    state->>'side' AS side,
    state->>'status' AS status,
    state->>'reason' AS reason,
    updated_at
FROM order_projection
ORDER BY updated_at DESC;

CREATE OR REPLACE VIEW v_positions_dashboard AS
SELECT
    symbol,
    (state->>'qty')::numeric AS qty,
    (state->>'avg_price')::numeric AS avg_price,
    (state->>'realized_pnl')::numeric AS realized_pnl,
    updated_at
FROM position_projection
ORDER BY symbol;

CREATE OR REPLACE VIEW v_dlq_dashboard AS
SELECT
    id,
    event_id,
    event_type,
    worker_name,
    error_type,
    error_message,
    resolved,
    created_at
FROM event_dead_letters
ORDER BY id DESC;
