BEGIN;

-- Единственная DB-функция допуска варианта к OOS. Она не меняет PASS-ворота:
-- отсеивает только неполные, устаревшие и непригодные для данного контура входы.
CREATE OR REPLACE FUNCTION analytics.oos_variant_admission_reason_v1(
    p_symbol text,
    p_timeframe text,
    p_parameters jsonb
) RETURNS text
LANGUAGE sql
STABLE
AS $$
WITH latest_roll AS (
    SELECT DISTINCT ON (root_symbol) root_symbol,selected_symbol
    FROM analytics.futures_roll_decision_v1
    ORDER BY root_symbol,created_at DESC
), symbol_root AS (
    SELECT CASE
      WHEN upper(p_symbol) ~ '^BR[A-Z][0-9]@RTSX$' THEN 'BR'
      WHEN upper(p_symbol) ~ '^NG[A-Z][0-9]@RTSX$' THEN 'NG'
      ELSE NULL
    END AS root_symbol
)
SELECT CASE
  WHEN NOT (coalesce(p_parameters,'{}'::jsonb) ? 'lookback')
    OR NOT (coalesce(p_parameters,'{}'::jsonb) ? 'threshold')
    OR NOT (coalesce(p_parameters,'{}'::jsonb) ? 'hold'
            OR coalesce(p_parameters,'{}'::jsonb) ? 'holding_bars')
    THEN 'OOS_SPECIFICATION_INCOMPLETE'
  WHEN upper(coalesce(p_timeframe,'')) = 'M1'
    THEN 'OOS_M1_MICROSTRUCTURE_REQUIRED'
  WHEN r.selected_symbol IS NOT NULL AND r.selected_symbol <> p_symbol
    THEN 'OOS_CONTRACT_ROLLED'
  ELSE 'ELIGIBLE'
END
FROM symbol_root sr
LEFT JOIN latest_roll r USING(root_symbol)
$$;

COMMENT ON FUNCTION analytics.oos_variant_admission_reason_v1(text,text,jsonb) IS
  'До OOS допускаются только полные варианты на активном фьючерсном контракте. M1 требует отдельный микроструктурный контур.';

ALTER TABLE analytics.oos_remediation_candidate_v1
  DROP CONSTRAINT IF EXISTS oos_remediation_candidate_v1_status_code_check;
ALTER TABLE analytics.oos_remediation_candidate_v1
  ADD CONSTRAINT oos_remediation_candidate_v1_status_code_check CHECK (status_code = ANY (ARRAY[
    'GENERATED','PRUNED_DUPLICATE','PRUNED_BUDGET','PRUNED_STALE',
    'WAITING_FUTURE_DATA','QUEUED','EVALUATED_FAIL','OOS_PASS'
  ]));

-- Сохраняем историю, но выводим из активной очереди только сценарии на
-- контракте, который DB-решение rollover уже заменило.
UPDATE analytics.oos_remediation_candidate_v1 c
SET status_code='PRUNED_STALE',
    reason_code=analytics.oos_variant_admission_reason_v1(c.symbol,'M5',c.parameter_json),
    updated_at=clock_timestamp()
WHERE c.status_code IN ('GENERATED','WAITING_FUTURE_DATA','QUEUED')
  AND analytics.oos_variant_admission_reason_v1(c.symbol,'M5',c.parameter_json)
      IN ('OOS_CONTRACT_ROLLED','OOS_SPECIFICATION_INCOMPLETE','OOS_M1_MICROSTRUCTURE_REQUIRED');

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('status.oos_specification_incomplete','ru','Неполные параметры','Параметры','Парам.','Вариант не содержит обязательные условия входа или выхода и не допускается к OOS.','','research'),
('status.oos_contract_rolled','ru','Контракт заменён','Ролловер','Ролл.','Фьючерс заменён актуальным контрактом по DB-решению rollover.','','research'),
('status.oos_m1_microstructure_required','ru','Нужен стакан M1','Стакан M1','M1','M1 не участвует в поиске прибыли без подтверждённого стакана и исполнения.','','research'),
('status.eligible','ru','Готов к OOS','Готов','OOS','Вариант полный и привязан к актуальному контракту.','','research'),
('status.oos_specification_incomplete','en','Incomplete parameters','Parameters','Params','Required entry or exit parameters are missing.','','research'),
('status.oos_contract_rolled','en','Contract rolled','Rollover','Roll','The future was replaced by the current contract.','','research'),
('status.oos_m1_microstructure_required','en','M1 order book required','M1 book','M1','M1 is excluded until order-book execution evidence is available.','','research'),
('status.eligible','en','OOS eligible','Eligible','OOS','The variant is complete and uses the current contract.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
  caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.failures.column.action','ru','Следующий шаг','Далее','Шаг','Единственное допустимое действие для первичной причины.','','research'),
('COST_REMEDIATION','ru','Усилить входы','Входы','Входы','Искать более сильные входы с реальными издержками, не ослабляя PASS.','','research'),
('SAMPLE_EXPANSION','ru','Расширить выборку','Выборка','Выборка','Накопить совместимые future-only наблюдения.','','research'),
('RECHECK_STATISTICAL','ru','Проверить статистику','Статистика','Стат.','Повторить статистическую проверку на новой когорте.','','research'),
('RECHECK_ROBUSTNESS','ru','Проверить устойчивость','Устойчивость','Уст.','Проверить соседние параметры.','','research'),
('RECHECK_HOLDOUT','ru','Открыть holdout','Holdout','Hold.','Выполнить независимую финальную проверку.','','research'),
('RECHECK_EXECUTION','ru','Проверить исполнение','Исполнение','Исп.','Накопить подтверждение стакана и исполнения.','','research'),
('RECHECK_CAPACITY','ru','Проверить ёмкость','Ёмкость','Ёмк.','Проверить лимит позиции относительно ликвидности.','','research'),
('RECHECK_PORTFOLIO','ru','Проверить портфель','Портфель','Портф.','Проверить независимый вклад в портфель.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,resource_group=EXCLUDED.resource_group;

GRANT EXECUTE ON FUNCTION analytics.oos_variant_admission_reason_v1(text,text,jsonb) TO alex,finam;

COMMIT;
