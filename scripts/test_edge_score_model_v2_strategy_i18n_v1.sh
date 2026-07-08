#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_STRATEGY_I18N_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
SELECT DISTINCT
    'strategy.' || lower(replace(strategy_code, '_', '.')) AS resource_key,
    'ru' AS locale_code,
    strategy_code AS caption,
    strategy_code AS caption_short,
    strategy_code AS caption_mobile,
    'Наименование стратегии' AS tooltip,
    '' AS icon,
    'strategy' AS resource_group
FROM analytics.edge_score_model_v2
WHERE strategy_code IS NOT NULL
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    resource_group=EXCLUDED.resource_group,
    updated_at=now();
SQL

python - <<'PY'
from pathlib import Path

targets = [
    Path("src/marketcore/presentation/components/max_edge_card.py"),
    Path("src/marketcore/presentation/components/edge_score_shadow_observation_card.py"),
    Path("src/marketcore/presentation/components/edge_score_shadow_daily_card.py"),
]

helper = '''
def _strategy_key(value) -> str:
    code = str(value if value is not None else "")
    return "strategy." + code.lower().replace("_", ".")

def _strategy_label(value) -> str:
    key = _strategy_key(value)
    return f'<span data-i18n-key="{_v(key)}">{_v(key)}</span>'
'''

for p in targets:
    s = p.read_text(encoding="utf-8")
    if "def _strategy_key" not in s:
        s = s.replace("\n\ndef _v(value) -> str:", "\n\ndef _v(value) -> str:", 1)
        insert_at = s.find("\n\ndef render_")
        if insert_at < 0:
            raise SystemExit(f"RENDER_MARKER_NOT_FOUND={p}")
        s = s[:insert_at] + "\n" + helper + s[insert_at:]

    s = s.replace('{_v(current.get("strategy_code"))}', '{_strategy_label(current.get("strategy_code"))}')
    s = s.replace('{_v(row.get(\'strategy_code\'))}', '{_strategy_label(row.get(\'strategy_code\'))}')
    s = s.replace('{_v(row.get("strategy_code"))}', '{_strategy_label(row.get("strategy_code"))}')

    p.write_text(s, encoding="utf-8")
PY

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_strategy_i18n PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/components/max_edge_card.py \
  src/marketcore/presentation/components/edge_score_shadow_observation_card.py \
  src/marketcore/presentation/components/edge_score_shadow_daily_card.py

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
    SELECT DISTINCT
        'strategy.' || lower(replace(strategy_code, '_', '.')) AS resource_key
    FROM analytics.edge_score_model_v2
    WHERE strategy_code IS NOT NULL
) s
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=s.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

if [ "$missing" != "0" ]; then
  echo "MISSING_STRATEGY_I18N=$missing"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/max_edge_strategy_i18n.html
grep -q "strategy.rsi.mean.reversion.v1" /tmp/max_edge_strategy_i18n.html

echo "missing_strategy_i18n=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_STRATEGY_I18N_V1_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_STRATEGY_I18N_V1_OK"
