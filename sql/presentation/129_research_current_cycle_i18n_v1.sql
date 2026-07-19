BEGIN;

INSERT INTO presentation.ui_resource_v1
    (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
    ('research.current.title','ru','Текущий поиск','Текущий поиск','Поиск','Краткое состояние последнего автономного цикла поиска edge.','','research'),
    ('research.current.status','ru','Статус','Статус','Статус','Текущее состояние процесса.','','research'),
    ('research.current.stage','ru','Этап','Этап','Этап','Выполняемый или последний завершённый этап.','','research'),
    ('research.current.progress','ru','Прогресс, %','Прогресс','Прогресс','Доля завершённых этапов текущего цикла.','','research'),
    ('research.current.reason','ru','Причина','Причина','Причина','Главная причина текущего результата или остановки.','','research'),
    ('research.current.next','ru','Далее','Далее','Далее','Следующее действие, выбранное системой.','','research'),
    ('research.current.running','ru','Идёт проверка','Проверка','Проверка','Финальный вердикт ещё не сформирован.','','research'),
    ('research.current.wait','ru','Дождаться этапа','Дождаться','Ждать','Система сама продолжает цикл; действие оператора не требуется.','','research'),
    ('research.domain.discover_regime','ru','Режим рынка','Режим','Режим','Определение текущих рыночных режимов для подбора стратегий.','','research'),
    ('research.domain.walkforward','ru','Проверка фолдов','Фолды','Фолды','Последовательная walk-forward проверка на временных фолдах.','','research'),
    ('research.domain.complete','ru','Завершено','Готово','Готово','Все этапы цикла завершены.','','research'),
    ('research.domain.orphan_queue_closed','ru','Очередь закрыта','Очередь','Очередь','Зависшая заявка закрыта монитором.','','research')
    ,('research.domain.discover_regime.tooltip','ru','Система определяет рыночные режимы.','Режимы','Режимы','Система определяет рыночные режимы.','','research')
    ,('research.domain.walkforward.tooltip','ru','Система проверяет варианты на временных фолдах.','Фолды','Фолды','Система проверяет варианты на временных фолдах.','','research')
    ,('research.domain.complete.tooltip','ru','Цикл поиска завершён.','Завершено','Готово','Цикл поиска завершён.','','research')
    ,('research.domain.orphan_queue_closed.tooltip','ru','Зависшая заявка закрыта монитором.','Очередь','Очередь','Зависшая заявка закрыта монитором.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
    resource_group=EXCLUDED.resource_group;

COMMIT;
