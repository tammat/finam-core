#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_ROBUSTNESS_I18N_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('paper.robustness.title','ru','Устойчивость Paper-модели','Устойчивость','Robust','Аудит устойчивости и риска переобучения','🛡','paper'),
('paper.robustness.robustness_score','ru','Robustness Score','Robustness','Robust','Оценка устойчивости модели','','paper'),
('paper.robustness.learning_readiness','ru','Learning Readiness','Learning','Learning','Готовность модели к обучению','','paper'),
('paper.robustness.sample_score','ru','Оценка выборки','Выборка','Выборка','Достаточность выборки','','paper'),
('paper.robustness.time_stability','ru','Временная устойчивость','Время','Время','Устойчивость по временным периодам','','paper'),
('paper.robustness.instrument_stability','ru','Устойчивость по инструментам','Инструменты','Инстр.','Устойчивость по инструментам','','paper'),
('paper.robustness.regime_stability','ru','Устойчивость по режимам','Режимы','Режимы','Устойчивость по режимам рынка','','paper'),
('paper.robustness.source_stability','ru','Устойчивость источников','Источники','Источ.','Устойчивость источников Trading Plan','','paper'),
('paper.robustness.overfit_risk','ru','Риск переобучения','Overfit','Overfit','Оценка риска переобучения','','paper'),
('paper.robustness.production_allowed','ru','Допуск в production','Production','Prod','Разрешение использовать результат в production','','paper')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group,
  updated_at=now();
SQL

echo "VERDICT=PAPER_EXECUTION_ROBUSTNESS_I18N_V1_READY"
