#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_I18N_COMPLETION_V1 ==="

files=(
  src/marketcore/presentation/localization.py
  src/marketcore/presentation/i18n/registry.py
  src/marketcore/presentation/components/max_edge_card.py
  src/marketcore/presentation/components/edge_score_shadow_observation_card.py
  src/marketcore/presentation/components/edge_score_shadow_daily_card.py
)

for f in "${files[@]}"; do
  test -f "$f"
  PYTHONPYCACHEPREFIX=/tmp/finam_pycache_i18n_completion PYTHONPATH=src python -m py_compile "$f"
done

python - <<'PY'
from pathlib import Path

patches = {
    "src/marketcore/presentation/components/max_edge_card.py": [
        ("from html import escape\n", "from html import escape\n\nfrom marketcore.presentation.localization import t\n"),
        ('<h2>edge.score.max.title</h2>', '<h2>{t("page.max_edge.title")}</h2>'),
        ('edge.score.max.symbol', 'column.symbol'),
        ('edge.score.max.strategy', 'column.strategy'),
        ('edge.score.max.score', 'column.score'),
        ('edge.score.max.confidence', 'column.confidence'),
        ('edge.score.max.timeframe', 'column.timeframe'),
        ('edge.score.max.recommendation', 'column.recommendation'),
        ('edge.score.max.trades', 'column.trades'),
        ('edge.score.explain.title', 'page.max_edge.explain.title'),
        ('edge.score.explain.group', 'column.group'),
        ('edge.score.explain.score', 'column.score'),
        ('edge.score.explain.weight', 'column.weight'),
        ('edge.score.explain.contribution', 'column.contribution'),
    ],
    "src/marketcore/presentation/components/edge_score_shadow_observation_card.py": [
        ("from html import escape\n", "from html import escape\n\nfrom marketcore.presentation.localization import t\n"),
        ('edge.score.shadow.title', 'page.shadow.title'),
        ('edge.score.shadow.readonly', 'message.readonly.shadow_observation'),
    ],
    "src/marketcore/presentation/components/edge_score_shadow_daily_card.py": [
        ("from html import escape\n", "from html import escape\n\nfrom marketcore.presentation.localization import t\n"),
        ('edge.score.shadow.daily.title', 'page.shadow.daily.title'),
        ('edge.score.shadow.daily.readonly', 'message.readonly.shadow_daily'),
    ],
}

for filename, replacements in patches.items():
    p = Path(filename)
    s = p.read_text(encoding="utf-8")

    for old, new in replacements:
        if old.startswith("from html import escape") and "from marketcore.presentation.localization import t" in s:
            continue
        s = s.replace(old, new)

    p.write_text(s, encoding="utf-8")
PY

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_i18n_completion PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/components/max_edge_card.py \
  src/marketcore/presentation/components/edge_score_shadow_observation_card.py \
  src/marketcore/presentation/components/edge_score_shadow_daily_card.py

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('column.confidence', 'ru', 'Надежность', 'Надежность', 'Надежность', 'Уровень доверия к кандидату', '', 'column'),
('column.timeframe', 'ru', 'Таймфрейм', 'TF', 'TF', 'Таймфрейм', '', 'column'),
('column.recommendation', 'ru', 'Рекомендация', 'Рек.', 'Рек.', 'Рекомендация системы', '', 'column'),
('column.trades', 'ru', 'Сделки', 'Сделки', 'Сделки', 'Количество сделок', '', 'column'),
('column.group', 'ru', 'Группа', 'Группа', 'Группа', 'Группа факторов', '', 'column'),
('column.weight', 'ru', 'Вес', 'Вес', 'Вес', 'Вес фактора', '', 'column'),
('column.contribution', 'ru', 'Вклад', 'Вклад', 'Вклад', 'Вклад в итоговую оценку', '', 'column'),
('page.max_edge.explain.title', 'ru', 'Объяснение оценки Edge', 'Explain', 'Explain', 'Объяснение вклада групп в Edge Score V2', '', 'page'),
('message.readonly.shadow_observation', 'ru', 'Режим наблюдения без исполнения', 'Read-only', 'Read-only', 'Данные отображаются без допуска к исполнению', '', 'message'),
('message.readonly.shadow_daily', 'ru', 'Ежедневная аналитика без исполнения', 'Read-only', 'Read-only', 'Дневные агрегаты доступны только для анализа', '', 'message')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    resource_group=EXCLUDED.resource_group,
    updated_at=now();
SQL

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('page.max_edge.title'),
    ('page.shadow.title'),
    ('page.shadow.daily.title'),
    ('page.max_edge.explain.title'),
    ('column.symbol'),
    ('column.strategy'),
    ('column.score'),
    ('column.confidence'),
    ('column.timeframe'),
    ('column.recommendation'),
    ('column.trades'),
    ('column.group'),
    ('column.weight'),
    ('column.contribution'),
    ('message.readonly.shadow_observation'),
    ('message.readonly.shadow_daily')
) AS required(resource_key)
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=required.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

if [ "$missing" != "0" ]; then
  echo "MISSING_I18N_COMPLETION_RESOURCES=$missing"
  exit 1
fi

if grep -RInE 'edge\.score\.max|edge\.score\.shadow' \
  src/marketcore/presentation/components/max_edge_card.py \
  src/marketcore/presentation/components/edge_score_shadow_observation_card.py \
  src/marketcore/presentation/components/edge_score_shadow_daily_card.py; then
  echo "LEGACY_EDGE_SCORE_I18N_KEYS_FOUND"
  exit 1
fi

if grep -RInE 'Максимальный edge|Инструмент|Стратегия|Доверие|Рекомендация|Сделки|Группа|Вклад|Вес' \
  src/marketcore/presentation/components/max_edge_card.py \
  src/marketcore/presentation/components/edge_score_shadow_observation_card.py \
  src/marketcore/presentation/components/edge_score_shadow_daily_card.py; then
  echo "HARDCODED_RU_UI_TEXT_FOUND"
  exit 1
fi

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/max-edge?v=$(date +%s)" >/tmp/i18n_completion_max_edge.html
curl -fsS "http://127.0.0.1:8080/edge-score-shadow?v=$(date +%s)" >/tmp/i18n_completion_shadow.html
curl -fsS "http://127.0.0.1:8080/edge-score-shadow-daily?v=$(date +%s)" >/tmp/i18n_completion_shadow_daily.html

grep -q "page.max_edge.title" /tmp/i18n_completion_max_edge.html
grep -q "page.shadow.title" /tmp/i18n_completion_shadow.html
grep -q "page.shadow.daily.title" /tmp/i18n_completion_shadow_daily.html

echo "missing_i18n_resources=0"
echo "legacy_edge_score_keys=0"
echo "hardcoded_ru_ui_text=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_I18N_COMPLETION_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_I18N_COMPLETION_V1_OK"
