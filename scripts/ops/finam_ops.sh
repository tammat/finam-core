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
  set -a
  # shellcheck disable=SC1091
  . /opt/finam-core/.env
  set +a
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
    echo "Меню управления Finam_Core"
    echo
    PS3="Выберите действие: "
    select item in \
      "dashboard" \
      "status" \
      "logs" \
      "health" \
      "accumulation" \
      "trades" \
      "bars-br" \
      "bars-ng" \
      "bars-usd" \
      "env" \
      "restart" \
      "выход"
    do
      case "$item" in
        "выход") echo "Выход"; break ;;
        "") echo "Неверный выбор" ;;
        *) "$0" "$item" ;;
      esac
      echo
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

  restart)
    sudo systemctl daemon-reload
    sudo systemctl restart finam-paper-pipeline.service
    systemctl status finam-paper-pipeline.service --no-pager
    ;;

  ng-gate)
    "$PY_BIN" src/scripts/runtime/run_ng_paper_pilot_v1.py
    ;;

  usd-gate)
    "$PY_BIN" src/scripts/runtime/run_usd_paper_pilot_v1.py
    ;;

  trades)
    psql "$DATABASE_URL" -c "
    SELECT symbol, side, qty, price, created_at
    FROM trades
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
    "$PY_BIN" src/scripts/analytics/build_accumulation_plan_v1.py | tee "$TMP_DIR/accumulation_plan_v1.out"
    echo "=== ACCUMULATION SUMMARY ==="
    grep -E "ACCUMULATION_PLAN_SUMMARY|CONTINUE_PAPER_ACCUMULATION|PAPER_CONFIRMATION_REQUIRED" \
      "$TMP_DIR/accumulation_plan_v1.out" || true
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
      grep -E "ERROR|Traceback|Exception|FAILED" || true

    echo
    echo "=== 3. ПЛАН НАКОПЛЕНИЯ СТАТИСТИКИ ==="
    "$PY_BIN" src/scripts/analytics/build_accumulation_plan_v1.py | tee "$TMP_DIR/accumulation_plan_v1.out"
    grep -E "ACCUMULATION_PLAN_SUMMARY|CONTINUE_PAPER_ACCUMULATION|PAPER_CONFIRMATION_REQUIRED" \
      "$TMP_DIR/accumulation_plan_v1.out" || true

    echo
    echo "=== 4. ПОСЛЕДНИЕ 20 СДЕЛОК ==="
    psql "$DATABASE_URL" -c "
    SELECT symbol, side, qty, price, created_at
    FROM trades
    ORDER BY created_at DESC
    LIMIT 20;
    "
    ;;

  health)
    echo "=== SERVICE ==="
    systemctl is-active finam-paper-pipeline.service || true
    echo "=== FAILED ==="
    systemctl --failed || true
    echo "=== RECENT ERRORS ==="
    $JOURNALCTL -u finam-paper-pipeline.service --since "60 minutes ago" --no-pager | \
    grep -E "ERROR|Traceback|Exception|FAILED" || true
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
