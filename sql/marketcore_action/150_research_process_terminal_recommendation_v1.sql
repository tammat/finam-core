BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.domain.no_action_required','ru','Действий не требуется','Готово','Готово','Процесс завершён, результат сохранён; дополнительных действий не требуется','','research'),
('research.domain.no_action_required.tooltip','ru','Процесс завершён и результат сохранён','Готово','Готово','Дополнительных действий оператора не требуется','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

CREATE OR REPLACE FUNCTION marketcore_action.finalize_research_recommendation_v1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.recommendation_code='WAIT_FOR_SYSTEM_ANALYSIS'
     AND (NEW.status_code='SUCCEEDED'
          OR (NEW.status_code='SKIPPED' AND NEW.outcome_code='CANCELLED')) THEN
    NEW.recommendation_code := 'NO_ACTION_REQUIRED';
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS research_process_terminal_recommendation_v1
ON marketcore_action.research_process_v1;
CREATE TRIGGER research_process_terminal_recommendation_v1
BEFORE UPDATE OF status_code,outcome_code,recommendation_code
ON marketcore_action.research_process_v1
FOR EACH ROW EXECUTE FUNCTION marketcore_action.finalize_research_recommendation_v1();

UPDATE marketcore_action.research_process_v1
SET recommendation_code='NO_ACTION_REQUIRED',
    explanation_ru=CASE
      WHEN explanation_ru IS NULL OR explanation_ru IN ('Процесс завершён','Системный процесс ожидает обновления')
      THEN 'Процесс завершён, результат сохранён'
      ELSE explanation_ru END,
    updated_at=clock_timestamp()
WHERE status_code='SUCCEEDED'
  AND outcome_code='COMPLETED'
  AND recommendation_code='WAIT_FOR_SYSTEM_ANALYSIS';

UPDATE marketcore_action.research_process_v1
SET recommendation_code='NO_ACTION_REQUIRED',updated_at=clock_timestamp()
WHERE status_code='SKIPPED'
  AND outcome_code='CANCELLED'
  AND recommendation_code='WAIT_FOR_SYSTEM_ANALYSIS';

COMMIT;
