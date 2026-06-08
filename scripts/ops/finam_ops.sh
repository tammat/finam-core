#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

# Русский комментарий:
# При запуске через глобальную команду fin окружение sudo может потерять DATABASE_URL.
# Поэтому подтягиваем переменные из systemd unit/env-file и inline Environment=.
if [ -z "${DATABASE_URL:-}" ]; then
  ENV_FILES=$(systemctl cat finam-paper-pipeline.service 2>/dev/null | sed -n 's/^EnvironmentFile=-\?//p' || true)
  for env_file in $ENV_FILES; do
    if [ -r "$env_file" ]; then
      set -a
      # shellcheck disable=SC1090
      . "$env_file"
      set +a
    fi
  done
fi

if [ -z "${DATABASE_URL:-}" ]; then
  while IFS= read -r env_line; do
    env_line="${env_line#Environment=}"
    env_line="${env_line%\"}"
    env_line="${env_line#\"}"
    case "$env_line" in
      DATABASE_URL=*) export "$env_line" ;;
      PG*=*) export "$env_line" ;;
    esac
  done < <(systemctl cat finam-paper-pipeline.service 2>/dev/null | grep '^Environment=' || true)
fi

if [ -z "${DATABASE_URL:-}" ] && [ -r "/opt/finam-core/.env" ]; then
  DATABASE_URL="$(
    grep -E '^DATABASE_URL=' /opt/finam-core/.env | tail -n 1 | cut -d= -f2-
  )"
  export DATABASE_URL
fi

if [ -x "/opt/finam-core/.venv/bin/python" ]; then
  PY_BIN="/opt/finam-core/.venv/bin/python"
elif [ -x "/opt/finam-core/venv/bin/python" ]; then
  PY_BIN="/opt/finam-core/venv/bin/python"
else
  PY_BIN="python3"
fi

JOURNALCTL="journalctl -q"
if sudo -n true 2>/dev/null; then
  JOURNALCTL="sudo journalctl -q"
fi

TMP_DIR="/var/tmp/finam-core-${USER:-unknown}"
mkdir -p "$TMP_DIR" 2>/dev/null || TMP_DIR="/tmp/finam-core-${USER:-unknown}"
mkdir -p "$TMP_DIR" 2>/dev/null || true

cmd="${1:-menu}"

case "$cmd" in

  menu)
    while true; do
      echo
      echo "=== МЕНЮ УПРАВЛЕНИЯ FINAM_CORE ==="
      echo " 1) dashboard      - общий дашборд"
      echo " 2) status         - статус сервиса"
      echo " 3) logs           - ключевые логи"
      echo " 4) health         - здоровье системы"
      echo " 5) accumulation   - план накопления статистики"
      echo " 6) trades         - последние сделки"
      echo " 7) bars-br        - бары Brent"
      echo " 8) bars-ng        - бары Natural Gas"
      echo " 9) bars-usd       - бары USD/RUB"
      echo "10) env            - параметры systemd/env"
      echo "11) restart        - безопасный restart"
      echo "12) guard-shadow   - shadow-отчёт Guard Execution Gate"
      echo "13) br-short       - BR short shadow/live status"
      echo "14) active-score   - активные контракты: статистика 7 дней"
      echo "15) active-score3  - активные контракты: статистика 3 дня"
      echo "16) rollover       - статус экспирации и rollover"
      echo "17) contract-align - сверка runtime-контрактов с календарём"
      echo " 0) выход"
      echo
      read -r -p "Выберите действие: " choice
      echo

      case "$choice" in
        1) echo "=== ДЕЙСТВИЕ: DASHBOARD ==="; "$0" dashboard ;;
        2) echo "=== ДЕЙСТВИЕ: STATUS ==="; "$0" status ;;
        3) echo "=== ДЕЙСТВИЕ: LOGS ==="; "$0" logs ;;
        4) echo "=== ДЕЙСТВИЕ: HEALTH ==="; "$0" health ;;
        5) echo "=== ДЕЙСТВИЕ: ACCUMULATION ==="; "$0" accumulation ;;
        6) echo "=== ДЕЙСТВИЕ: TRADES ==="; "$0" trades ;;
        7) echo "=== ДЕЙСТВИЕ: BARS-BR ==="; "$0" bars-br ;;
        8) echo "=== ДЕЙСТВИЕ: BARS-NG ==="; "$0" bars-ng ;;
        9) echo "=== ДЕЙСТВИЕ: BARS-USD ==="; "$0" bars-usd ;;
        10) echo "=== ДЕЙСТВИЕ: ENV ==="; "$0" env ;;
        11) echo "=== ДЕЙСТВИЕ: RESTART ==="; "$0" restart ;;
        12) echo "=== ДЕЙСТВИЕ: GUARD SHADOW REPORT ==="; "$0" guard-shadow ;;
        13) echo "=== ДЕЙСТВИЕ: BR SHORT STATUS ==="; "$0" br-short ;;
        14) echo "=== ДЕЙСТВИЕ: ACTIVE CONTRACT SCORECARD 7D ==="; "$0" active-score ;;
        15) echo "=== ДЕЙСТВИЕ: ACTIVE CONTRACT SCORECARD 3D ==="; "$0" active-score3 ;;
        16) echo "=== ДЕЙСТВИЕ: ROLLOVER STATUS ==="; "$0" rollover ;;
        17) echo "=== ДЕЙСТВИЕ: CONTRACT ALIGNMENT ==="; "$0" contract-align ;;
        0) echo "Выход"; exit 0 ;;
        *) echo "Неверный выбор: $choice" ;;
      esac
    done
    ;;
  status)
    systemctl status finam-paper-pipeline.service --no-pager
    ;;

  logs)
    $JOURNALCTL -u finam-paper-pipeline.service --since "${2:-30 minutes ago}" --no-pager | \
    grep -E "PIPE_SESSION_BLOCK|PIPE_NG|PIPE_USD|NG_PAPER|USD_PAPER|PaperExecution|FILL|TRADE|ERROR|Traceback" || true
    ;;

  follow)
    $JOURNALCTL -u finam-paper-pipeline.service -f --no-pager | \
    grep -E "PIPE_SESSION_BLOCK|PIPE_NG|PIPE_USD|NG_PAPER|USD_PAPER|PaperExecution|FILL|TRADE|ERROR|Traceback"
    ;;

  env)
    systemctl cat finam-paper-pipeline.service | \
    grep -E "ENABLE_NG|NG_PAPER|NG_M1|ENABLE_USD|USD_PAPER|EXECUTION_MODE|REAL_TRADING|PAPER"
    ;;

  active-score)
    cd /opt/finam-core
    export PYTHONPATH=src
    WINDOW_DAYS=7 python src/scripts/analytics/build_active_contract_scorecard_v1_1_recent_window.py
    ;;

  active-score3)
    cd /opt/finam-core
    export PYTHONPATH=src
    WINDOW_DAYS=3 python src/scripts/analytics/build_active_contract_scorecard_v1_1_recent_window.py
    ;;

  rollover)
    cd /opt/finam-core
    export PYTHONPATH=src
    python src/scripts/analytics/build_rollover_status_report_v1.py
    ;;

  contract-align)
    cd /opt/finam-core
    export PYTHONPATH=src
    python src/scripts/analytics/build_runtime_active_contract_vs_calendar_v1.py
    ;;


  guard-shadow)
    "$PY_BIN" src/scripts/analytics/build_guard_shadow_effectiveness_report_v1.py --since "24 hours ago"
    ;;

  energy-policy)
    "$PY_BIN" src/scripts/analytics/build_energy_direction_policy_status_v1.py
    ;;

  br-short)
    "$PY_BIN" src/scripts/analytics/build_br_short_shadow_live_report_v1.py
    ;;

  restart)
    echo "Перезапуск сервиса требует прав sudo."
    echo "Выполните из-под пользователя alex:"
    echo
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl restart finam-paper-pipeline.service"
    echo "  systemctl status finam-paper-pipeline.service --no-pager"
    ;;

  ng-gate)
    "$PY_BIN" src/scripts/runtime/run_ng_paper_pilot_v1.py
    ;;

  usd-gate)
    "$PY_BIN" src/scripts/runtime/run_usd_paper_pilot_v1.py
    ;;

  trades)
    psql "$DATABASE_URL" -c "
    SELECT
        symbol,
        side,
        qty,
        round(price::numeric, 4) AS price,
        to_char(created_at AT TIME ZONE 'Europe/Moscow', 'DD-MM-YYYY HH24:MI:SS') AS created_at_msk
    FROM trades
    WHERE symbol IN ('BRN6@RTSX','NGN6@RTSX','USDRUBF@RTSX')
      AND COALESCE(origin, '') = 'paper'
      AND COALESCE(is_invalid, false) = false
    ORDER BY created_at DESC
    LIMIT 20;
    "
    ;;

  bars-ng)
    psql "$DATABASE_URL" -c "
    SELECT symbol, timeframe, count(*) bars, min(ts) first_bar, max(ts) last_bar
    FROM market_bars
    WHERE symbol LIKE 'NG%'
    GROUP BY symbol,timeframe
    ORDER BY symbol,timeframe;
    "
    ;;

  bars-usd)
    psql "$DATABASE_URL" -c "
    SELECT symbol, timeframe, count(*) bars, min(ts) first_bar, max(ts) last_bar
    FROM market_bars
    WHERE symbol='USDRUBF@RTSX'
    GROUP BY symbol,timeframe
    ORDER BY timeframe;
    "
    ;;

  bars-br)
    psql "$DATABASE_URL" -c "
    SELECT symbol, timeframe, count(*) bars, min(ts) first_bar, max(ts) last_bar
    FROM market_bars
    WHERE symbol LIKE 'BR%'
    GROUP BY symbol,timeframe
    ORDER BY symbol,timeframe;
    "
    ;;

  accumulation)
    echo "=== ACCUMULATION PLAN V1 ==="
    "$PY_BIN" src/scripts/observability/build_accumulation_summary_ru_v1.py
    ;;

  dashboard)
    echo "=== ДАШБОРД FINAM_CORE ==="
    echo
    echo "=== 1. СЕРВИС ==="
    systemctl is-active finam-paper-pipeline.service || true
    systemctl status finam-paper-pipeline.service --no-pager | sed -n '1,12p' || true

    echo
    echo "=== 2. ОШИБКИ ЗА 60 МИНУТ ==="
    $JOURNALCTL -u finam-paper-pipeline.service --since "60 minutes ago" --no-pager | \
      grep -E "ERROR|Traceback|Exception|FAILED" | grep -v "PIPE_SESSION_BLOCK phase=preopen" || true

    echo
    echo "=== 3. ИССЛЕДОВАТЕЛЬСКИЙ КОНТУР ==="

    "$PY_BIN" \
    src/scripts/observability/build_research_kpi_dashboard_v1.py

    echo
    "$PY_BIN" src/scripts/observability/build_edge_scorecard_v1.py
    echo
    echo "=== 3.1. CRYPTO RESEARCH ==="
    "$PY_BIN" src/scripts/observability/build_crypto_research_dashboard_v1.py || true

    echo
    echo "=== 3.2. CRYPTO FEATURES ==="
    "$PY_BIN" src/scripts/observability/build_crypto_feature_dashboard_v1.py || true

    echo
    echo "=== 3.3. REGIME GUARD SHADOW ==="
    "$PY_BIN" src/scripts/research/build_regime_guard_shadow_report_v1.py --since "24 hours" || true

    echo
    echo "=== 3.4. REGIME GUARD SHADOW EFFECTIVENESS ==="
    "$PY_BIN" src/scripts/research/build_regime_guard_shadow_effectiveness_report_v1.py --since "24 hours" || true

    echo
    echo "=== 4. СВЕЖЕСТЬ БАРОВ BR/NG/USD ==="
    psql "$DATABASE_URL" -c "
    SELECT
      symbol,
      timeframe,
      to_char(max(ts) AT TIME ZONE 'Europe/Moscow','DD-MM-YYYY HH24:MI:SS') AS last_bar_msk,
      round(extract(epoch from (now() - max(ts))) / 60, 2) AS lag_min
    FROM market_bars
    WHERE symbol IN ('BRN6@RTSX','NGN6@RTSX','USDRUBF@RTSX')
      AND timeframe IN ('M1','M5')
    GROUP BY symbol, timeframe
    ORDER BY symbol, timeframe;
    "

    echo "=== 4. БЛОКИРОВКИ СИГНАЛОВ ЗА 30 МИНУТ ==="
    blocks_tmp="$(mktemp)"
    journalctl -u finam-paper-pipeline.service --since "30 minutes ago" --no-pager 2>/dev/null | \
      grep "RUNTIME_GUARD_PRE_SIGNAL_BLOCK_SAVED" | \
      sed -E 's/.*symbol=([^ ]+).*block_type=([^ ]+).*/\1 \2/' | \
      sort | uniq -c | tee "$blocks_tmp" || true

    blocked_total="$(awk '{s += $1} END {print s + 0}' "$blocks_tmp")"
    echo "BLOCKED_SIGNALS_TOTAL=${blocked_total}"
    rm -f "$blocks_tmp"


    echo
    echo
    "$PY_BIN" src/scripts/observability/build_execution_funnel_v2.py


    echo
    echo "=== 5. ПОСЛЕДНИЕ FILL BR/NG ЗА 1 ЧАС ==="
    psql "$DATABASE_URL" -c "
    SELECT
        symbol,
        side,
        qty,
        price,
        origin,
        strategy,
        timeframe,
        created_at
    FROM trades
    WHERE symbol IN ('BRN6@RTSX','NGN6@RTSX')
      AND created_at >= now() - interval '1 hour'
      AND COALESCE(origin, '') = 'paper'
      AND is_invalid = false
    ORDER BY created_at DESC
    LIMIT 20;
    "

    echo
    echo "=== 6. ПОСЛЕДНИЕ 20 PAPER-СДЕЛОК ==="
    psql "$DATABASE_URL" -c "
    SELECT
        symbol,
        side,
        qty,
        price,
        origin,
        strategy,
        timeframe,
        created_at
    FROM trades
    WHERE origin = 'paper'
      AND is_invalid = false
      AND COALESCE(strategy, '') <> ''
      AND COALESCE(payload->>'source', '') <> 'moex_external_replay_v3'
      AND COALESCE(payload->>'regime', '') <> 'MOEX_HISTORY'
      AND COALESCE(payload->>'paper_only', '') <> 'true'
    ORDER BY created_at DESC
    LIMIT 20;
    "
    ;;

  health)
    echo "=== RESEARCH FEATURE FRESHNESS HEALTH ==="
    "$PY_BIN" src/scripts/observability/build_research_feature_freshness_health_v1.py || true
    echo
    echo "=== ДЕЙСТВИЕ: HEALTH ==="
    echo "Время проверки МСК: $(TZ=Europe/Moscow date '+%d-%m-%Y %H:%M:%S')"
    echo
    echo "=== SERVICE ==="
    systemctl is-active finam-paper-pipeline.service || true
    echo "=== FAILED ==="
    systemctl --failed || true
    echo "=== BROKER SYNC ==="
    broker_sync_errors="$($JOURNALCTL -u finam-paper-pipeline.service --since "60 minutes ago" --no-pager | grep -c "PIPE_BROKER_POSITION_SYNC_ERROR" || true)"
    if [ "$broker_sync_errors" -gt 0 ]; then
      echo "status=WARN"
      echo "errors_last_60m=${broker_sync_errors}"
    else
      echo "status=OK"
    fi
    echo
    echo "=== RECENT ERRORS ==="
    $JOURNALCTL -u finam-paper-pipeline.service --since "60 minutes ago" --no-pager | \
    grep -E "ERROR|Traceback|Exception|FAILED" | grep -v "PIPE_SESSION_BLOCK phase=preopen" || true
    ;;

  help|*)
    cat <<'EOF'
Finam_Core ops commands:

  dashboard       - общий дашборд: сервис, ошибки, накопление, последние сделки
  status          - статус finam-paper-pipeline
  logs [period]   - ключевые логи за период, по умолчанию 30 minutes ago
  follow          - live-мониторинг NG/USD/FILL/ERROR
  env             - переменные systemd по pilot/runtime
  restart         - daemon-reload + restart pipeline
  ng-gate         - ручная проверка NG Paper Pilot gate
  usd-gate        - ручная проверка USD Paper Pilot gate
  trades          - последние 20 сделок
  bars-ng         - история NG
  bars-usd        - история USDRUBF
  bars-br         - история BR
  accumulation    - план накопления paper-статистики для повторной edge-валидации
  health          - быстрый healthcheck сервиса и ошибок
  menu            - интерактивное меню ops-команд

Examples:
  ./scripts/ops/finam_ops.sh logs
  ./scripts/ops/finam_ops.sh logs "2 hours ago"
  ./scripts/ops/finam_ops.sh usd-gate
EOF
    ;;
esac
