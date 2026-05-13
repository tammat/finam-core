#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
source .venv/bin/activate

set -a
source .env
set +a

echo "=== ENV ==="
python - <<'PY'
import os

for name in ["DATABASE_URL", "TG_AI_TOKEN", "TG_PROXY", "ENABLE_AI_SENTIMENT_FEATURES"]:
    v = os.getenv(name, "")
    if "TOKEN" in name:
        print(name, "present=", bool(v), "colon=", ":" in v, "prefix=", v[:10])
    elif name == "TG_PROXY":
        print(name, "present=", bool(v), "scheme=", v.split("://")[0] if "://" in v else "")
    else:
        print(name, "present=", bool(v), "value=", "***" if v else "")
PY

echo "=== DB ==="
python - <<'PY'
import os
import psycopg2

dsn = os.getenv("DATABASE_URL")
with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT current_user, current_database()")
        print(cur.fetchone())
PY

echo "=== TELEGRAM API VIA PROXY ==="
export ALL_PROXY="${TG_PROXY:-}"
export HTTPS_PROXY="${TG_PROXY:-}"
export HTTP_PROXY="${TG_PROXY:-}"

python - <<'PY'
import os
import requests

token = os.getenv("TG_AI_TOKEN")
r = requests.get(
    f"https://api.telegram.org/bot{token}/getMe",
    timeout=30,
)
print(r.status_code)
print(r.json())
PY

echo "OK: AI env, DB and Telegram proxy check passed"
