#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

cmd="${1:-help}"

case "$cmd" in
  status)
    systemctl status finam-paper-pipeline.service --no-pager
    ;;

  logs)
    journalctl -u finam-paper-pipeline.service --since "${2:-30 minutes ago}" --no-pager | \
    grep -E "PIPE_SESSION_BLOCK|PIPE_NG|PIPE_USD|NG_PAPER|USD_PAPER|PaperExecution|FILL|TRADE|ERROR|Traceback" || true
    ;;

  follow)
    journalctl -u finam-paper-pipeline.service -f --no-pager | \
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
    python src/scripts/runtime/run_ng_paper_pilot_v1.py
    ;;

  usd-gate)
    python src/scripts/runtime/run_usd_paper_pilot_v1.py
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

  health)
    echo "=== SERVICE ==="
    systemctl is-active finam-paper-pipeline.service || true
    echo "=== FAILED ==="
    systemctl --failed || true
    echo "=== RECENT ERRORS ==="
    journalctl -u finam-paper-pipeline.service --since "60 minutes ago" --no-pager | \
    grep -E "ERROR|Traceback|Exception|FAILED" || true
    ;;

  help|*)
    cat <<'EOF'
Finam_Core ops commands:

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
  health          - быстрый healthcheck сервиса и ошибок

Examples:
  ./scripts/ops/finam_ops.sh logs
  ./scripts/ops/finam_ops.sh logs "2 hours ago"
  ./scripts/ops/finam_ops.sh usd-gate
EOF
    ;;
esac
