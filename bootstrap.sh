#!/usr/bin/env bash
set -e

echo "=== Finam Core Bootstrap ==="

# ---------------------------
# 1. System update
# ---------------------------
apt update && apt upgrade -y

# ---------------------------
# 2. Base packages
# ---------------------------
apt install -y \
  python3 python3-venv python3-pip \
  git curl build-essential \
  libpq-dev postgresql postgresql-contrib

# ---------------------------
# 3. PostgreSQL setup
# ---------------------------
echo "=== Setup PostgreSQL ==="

sudo -u postgres psql <<EOF
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'finam_core') THEN
      CREATE DATABASE finam_core;
   END IF;
END
\$\$;

DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'finam') THEN
      CREATE USER finam WITH PASSWORD 'finam_pass';
   END IF;
END
\$\$;

ALTER ROLE finam SET client_encoding TO 'utf8';
ALTER ROLE finam SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE finam_core TO finam;
EOF

# ---------------------------
# 4. Clone project
# ---------------------------
echo "=== Clone repo ==="

cd /opt
if [ ! -d "finam-core" ]; then
  git clone https://github.com/tammat/finam-core.git
fi

cd finam-core

# ---------------------------
# 5. Python env
# ---------------------------
echo "=== Setup Python venv ==="

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ---------------------------
# 6. ENV setup
# ---------------------------
echo "=== Setup ENV ==="

mkdir -p deploy/env

cat > deploy/env/.env <<EOF
FINAM_ACCOUNT_ID=1943312
FINAM_GRPC_HOST=api.finam.ru:443

FINAM_SECRET=PUT_YOUR_SECRET_HERE

DATABASE_URL=postgresql://finam:finam_pass@localhost:5432/finam_core

EXECUTION_MODE=paper
RISK_SOFT=1

ENABLE_TELEGRAM_NOTIFIER=0

BROKER_FEE_RATE=0.0004
EXCHANGE_FEE_RATE=0.0001

ENTRY_COOLDOWN_SEC=300
EOF

# ---------------------------
# 7. DB schema
# ---------------------------
echo "=== Create tables ==="

psql "postgresql://finam:finam_pass@localhost:5432/finam_core" <<EOF
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    symbol TEXT,
    side TEXT,
    qty DOUBLE PRECISION,
    price DOUBLE PRECISION,
    ts TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    symbol TEXT,
    signal TEXT,
    meta JSONB,
    ts TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_events (
    id SERIAL PRIMARY KEY,
    event TEXT,
    payload JSONB,
    ts TIMESTAMP DEFAULT NOW()
);
EOF

# ---------------------------
# 8. run.sh
# ---------------------------
echo "=== Create run.sh ==="

cat > run.sh <<'EOF'
#!/usr/bin/env bash
set -e

cd /opt/finam-core
source .venv/bin/activate

set -a
source deploy/env/.env
set +a

export PYTHONPATH=src

python -u src/scripts/run_market_pipeline.py \
  --symbol BRM6@RTSX \
  --symbols BRM6@RTSX \
  --strategy vwap_bands_mr \
  --run-secs 0 \
  --risk-soft \
  --enable-filter-engine
EOF

chmod +x run.sh

# ---------------------------
# 9. systemd service
# ---------------------------
echo "=== Setup systemd ==="

cat > /etc/systemd/system/finam-core.service <<EOF
[Unit]
Description=Finam Core Trading Engine
After=network.target

[Service]
User=root
WorkingDirectory=/opt/finam-core
ExecStart=/opt/finam-core/run.sh
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable finam-core

# ---------------------------
# 10. Start
# ---------------------------
echo "=== Starting service ==="

systemctl start finam-core

sleep 3

systemctl status finam-core --no-pager

echo "=== DONE ==="
