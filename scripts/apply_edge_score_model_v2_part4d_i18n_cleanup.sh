#!/usr/bin/env bash
set -euo pipefail

echo "=== APPLY_EDGE_SCORE_MODEL_V2_PART4D_I18N_CLEANUP ==="

target="src/marketcore/presentation/components/max_edge_card.py"
test -f "$target"

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/components/max_edge_card.py")
s = p.read_text(encoding="utf-8")

replacements = {
    "🎯 Максимальный edge": "edge.score.max.title",
    "Инструмент": "edge.score.max.symbol",
    "Стратегия": "edge.score.max.strategy",
    "Score": "edge.score.max.score",
    "Доверие": "edge.score.max.confidence",
    "TF:": "edge.score.max.timeframe",
    "Рекомендация:": "edge.score.max.recommendation",
    "Сделки:": "edge.score.max.trades",
}

for old, key in replacements.items():
    s = s.replace(old, key)

p.write_text(s, encoding="utf-8")
print("patch_status=applied")
PY

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('edge.score.max.title', 'ru', 'Максимальный edge', 'Max Edge', 'Max Edge', 'Карточка максимального edge', '', 'edge_score'),
('edge.score.max.symbol', 'ru', 'Инструмент', 'Инструмент', 'Инструмент', 'Торговый инструмент', '', 'edge_score'),
('edge.score.max.strategy', 'ru', 'Стратегия', 'Стратегия', 'Стратегия', 'Код стратегии', '', 'edge_score'),
('edge.score.max.score', 'ru', 'Score', 'Score', 'Score', 'Итоговая оценка edge', '', 'edge_score'),
('edge.score.max.confidence', 'ru', 'Доверие', 'Доверие', 'Доверие', 'Уровень доверия к кандидату', '', 'edge_score'),
('edge.score.max.timeframe', 'ru', 'Таймфрейм', 'TF', 'TF', 'Таймфрейм стратегии', '', 'edge_score'),
('edge.score.max.recommendation', 'ru', 'Рекомендация', 'Рек.', 'Рек.', 'Рекомендация по кандидату', '', 'edge_score'),
('edge.score.max.trades', 'ru', 'Сделки', 'Сделки', 'Сделки', 'Количество сделок', '', 'edge_score')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    resource_group=EXCLUDED.resource_group,
    updated_at=now();
SQL

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile "$target"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART4D_I18N_CLEANUP_PATCH_READY"
