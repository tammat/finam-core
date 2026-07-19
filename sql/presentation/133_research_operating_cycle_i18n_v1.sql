BEGIN;
INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.operating.title','ru','Рабочий цикл','Цикл','Цикл','Текущая фаза автономной цепочки и ближайший запуск.','','research'),
('research.operating.phase','ru','Фаза','Фаза','Фаза','Текущий этап обработки рыночных данных.','','research'),
('research.operating.status','ru','Статус','Статус','Статус','Готовность текущей части цепочки.','','research'),
('research.operating.next','ru','Следующий запуск','Далее','Далее','Время открытия следующей разрешённой рыночной сессии.','','research'),
('research.operating.session_open','ru','Сессия открыта','Открыто','Открыто','Поток должен работать сейчас.','','research'),
('research.operating.audit','ru','Исторический цикл','История','История','Состояние системного полного исторического прогона.','','research'),
('research.domain.waiting','ru','Ожидание','Ожидание','Ждём','Система ожидает разрешённого торгового окна.','','status'),
('research.domain.quotes','ru','Котировки','Котировки','Котировки','Проверяется свежесть реального потока котировок.','','status'),
('research.domain.signals','ru','Сигналы','Сигналы','Сигналы','Проверяется создание новых сигналов.','','status'),
('research.domain.trades','ru','Сделки','Сделки','Сделки','Проверяется прохождение заявок и модельных сделок.','','status'),
('research.domain.research','ru','Исследование','Исследование','Анализ','Свежие сделки преобразуются в исследовательские результаты.','','status'),
('research.domain.oos','ru','OOS','OOS','OOS','Выполняется независимая вневыборочная проверка.','','status'),
('research.domain.attention','ru','Внимание','Внимание','Внимание','Цепочка работает, но ожидает следующий тип данных.','','status'),
('research.domain.enqueued','ru','В очереди','В очереди','Очередь','Исторический цикл принят системой.','','status'),
('research.domain.active_request_exists','ru','Выполняется','Выполняется','Работает','Новая заявка не создана: цикл уже выполняется.','','status'),
('research.domain.already_enqueued','ru','Уже поставлен','Уже в очереди','Очередь','Повторная заявка безопасно отклонена.','','status'),
('research.domain.not_run','ru','Не запускался','Нет запуска','Нет','Цикл ещё не запускался.','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 resource_group=excluded.resource_group;
COMMIT;
