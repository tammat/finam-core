# Finam Core — Maintenance

## Safe cleanup of test projections

Русский комментарий:
Скрипт используется только для безопасной очистки тестовых projection-таблиц и DLQ.

Разрешённые таблицы:

- position_projection
- order_projection
- event_dead_letters

Перед очисткой выводится текущее количество строк.

Run:

    CONFIRM_CLEAR_TEST_PROJECTIONS=1 DATABASE_URL="$DATABASE_URL" bash scripts/clear_test_projections_safe.sh

Expected result:

    CLEARED_TEST_PROJECTIONS_OK

Validation:

    bash scripts/test_safe_cleanup_docs.sh
