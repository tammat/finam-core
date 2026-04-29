#!/usr/bin/env bash
set -euo pipefail

APP_USER="${APP_USER:-finam}"
APP_DIR="${APP_DIR:-/opt/finam-core}"
REPO_URL="${REPO_URL:-https://github.com/tammat/finam-core.git}"
BRANCH="${BRANCH:-feature/bars-ingestion-storage}"
DB_NAME="${DB_NAME:-finam_core}"
DB_USER="${DB_USER:-finam}"
DB_PASSWORD="${DB_PASSWORD:-finam_pass}"
SERVICE_NAME="${SERVICE_NAME:-finam-core}"

log() { echo "[BOOTSTRAP] $*"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo bash bootstrap.sh" >&2
  exit 1
fi

log "Install packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl git build-essential \
  python3 python3-venv python3-pip \
  libpq-dev postgresql postgresql-contrib \
  jq dnsutils netcat-openbsd

log "Create app user"
id "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$APP_USER"

log "Setup PostgreSQL"
sudo -u postgres psql <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
      CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
   END IF;
END
\$\$;

SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec

ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';
ALTER ROLE ${DB_USER} SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

log "Clone/update repo"
mkdir -p "$(dirname "$APP_DIR")"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

log "Setup Python venv"
sudo -u "$APP_USER" bash -lc "cd '$APP_DIR' && python3 -m venv .venv"
sudo -u "$APP_USER" bash -lc "cd '$APP_DIR' && .venv/bin/pip install --upgrade pip setuptools wheel"
sudo -u "$APP_USER" bash -lc "cd '$APP_DIR' && .venv/bin/pip install -r requirements.txt"

log "Create env if missing"
mkdir -p "$APP_DIR/deploy/env"
if [ ! -f "$APP_DIR/deploy/env/.env" ]; then
  cat > "$APP_DIR/deploy/env/.env" <<ENV
FINAM_ACCOUNT_ID=1943312
FINAM_GRPC_HOST=api.finam.ru:443
FINAM_SECRET=PUT_YOUR_FINAM_SECRET_HERE

DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}

EXECUTION_MODE=paper
RISK_SOFT=1
RUN_SECS=0
SYMBOL=BRM6@RTSX
SYMBOLS=BRM6@RTSX
PIPELINE_STRATEGY=vwap_bands_mr

ENABLE_FILTER_ENGINE=1
TRADEABILITY_GATE=range_atr_band
TRADEABILITY_MIN_RANGE_ATR=0.1
TRADEABILITY_MAX_RANGE_ATR=6.0

BROKER_FEE_RATE=0.0004
EXCHANGE_FEE_RATE=0.0001
MIN_BROKER_FEE=0.0
TAX_RESERVE_RATE=0.13

TRAILING_STOP_ABS=0.30
TAKE_PROFIT_ABS=0.60
TRAILING_STEP_ABS=0.30
ENTRY_COOLDOWN_SEC=300

ENABLE_TELEGRAM_NOTIFIER=0
TG_TOKEN=PUT_YOUR_TELEGRAM_TOKEN_HERE
TG_CHAT_ID=PUT_YOUR_CHAT_ID_HERE
ENV
fi
chmod 600 "$APP_DIR/deploy/env/.env"
chown "$APP_USER:$APP_USER" "$APP_DIR/deploy/env/.env"

log "Create run.sh"
cat > "$APP_DIR/run.sh" <<'RUN'
#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

set -a
source deploy/env/.env
set +a

source .venv/bin/activate
export PYTHONPATH=src
export PYTHONUNBUFFERED=1

python -u src/scripts/run_market_pipeline.py \
  --symbol "${SYMBOL:-BRM6@RTSX}" \
  --symbols "${SYMBOLS:-${SYMBOL:-BRM6@RTSX}}" \
  --strategy "${PIPELINE_STRATEGY:-vwap_bands_mr}" \
  --run-secs "${RUN_SECS:-0}" \
  --quote-log-every "${QUOTE_LOG_EVERY:-30}" \
  --enable-filter-engine
RUN
chmod +x "$APP_DIR/run.sh"
chown "$APP_USER:$APP_USER" "$APP_DIR/run.sh"

log "Apply DB schema"
PGPASSWORD="$DB_PASSWORD" psql -h localhost -U "$DB_USER" -d "$DB_NAME" <<SQL
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION DEFAULT 0,
    fill_id TEXT,
    origin TEXT,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT,
    strategy TEXT,
    side TEXT,
    qty DOUBLE PRECISION,
    status TEXT NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_events (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT,
    event TEXT NOT NULL,
    decision TEXT,
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS account_snapshots (
    id BIGSERIAL PRIMARY KEY,
    account_id TEXT NOT NULL,
    equity DOUBLE PRECISION,
    unrealized_profit DOUBLE PRECISION,
    available_cash DOUBLE PRECISION,
    initial_margin DOUBLE PRECISION,
    maintenance_margin DOUBLE PRECISION,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_created_at ON trades(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_created_at ON signals(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_events_symbol_created_at ON risk_events(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_account_snapshots_created_at ON account_snapshots(created_at DESC);
SQL

log "Create systemd service"
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<SERVICE
[Unit]
Description=Finam Core Trading Engine
Wants=network-online.target postgresql.service
After=network-online.target postgresql.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/deploy/env/.env
ExecStart=${APP_DIR}/run.sh
Restart=always
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=30
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"

log "Network check"
dig +short api.finam.ru || true
nc -vz api.finam.ru 443 || true

cat <<MSG

=== BOOTSTRAP DONE ===

1) Edit secrets:
   nano ${APP_DIR}/deploy/env/.env

2) Start/restart:
   systemctl restart ${SERVICE_NAME}

3) Logs:
   journalctl -u ${SERVICE_NAME} -f

Current mode: PAPER. Real orders are NOT enabled.
MSG
