# MarketCore — чекпоинт состояния

Обновлено: 29.07.2026, 09:09 МСК.

## Главная цель

Найти воспроизводимый торговый edge, подтверждённый на независимых данных после реальных комиссий, спреда и проскальзывания, затем безопасно провести его через OOS → Forward → Shadow → Paper. Реальная торговля остаётся заблокированной до полного PASS.

## Единственный текущий приоритет

Восстановить и проверить замкнутую накопительную цепочку:

`котировка → сигнал → Paper-заявка → Paper-позиция → закрытие → чистая когорта → накопительный счётчик связки → автоматическая OOS-очередь`.

До подтверждения этой цепочки не менять методологию, не расширять UI и не добавлять новые семейства стратегий, кроме исправления критических ошибок.

## Последнее подтверждённое состояние

Последняя проверка фактической статистики проводилась по данным до 25.07.2026. Перед продолжением цифры требуется повторно сверить с БД на сервере `deb`.

- Службы `finam-paper-pipeline`, `finam-paper-safe` и `finam-readonly-ui` были активны после перезапуска.
- UI: `http://onezh.ddns.net:18080/workspace-v2`.
- Рабочая чистая когорта: V4. V3 сохранена как архивное основание и не смешивается с V4.
- Последние подтверждённые объёмы закрытий:
  - `FRESH_V3_EQUITY`: 89;
  - `FRESH_V3_FUTURES`: 6;
  - `FRESH_V4_REGIME_EQUITY`: 799;
  - `FRESH_V4_REGIME_FUTURES`: 76.
- После 25.07 новых подтверждённых FRESH-закрытий не наблюдалось; это главный разрыв, который надо проверить первым.
- Подтверждённых OOS PASS пока нет.

## Проверка автономных поисков 28.07.2026, 12:12 МСК

| Контур | Состояние | Как запускается | Последнее подтверждение |
|---|---|---|---|
| Intraday | Работает | системный таймер проверяет каждые 15 минут; полный цикл разрешён раз в 60 минут | 28.07.2026 12:12 МСК: `FINISHED`, планировщик 1, обработчик 1, ошибок 0 |
| Swing | Работает по закрытым барам | единый DB-планировщик; отдельный конкурирующий таймер не создаётся | 28.07.2026 06:05 МСК: `COMPLETE`, обработаны D1/H1/H4 |

- Исправлена ошибка Intraday: холостые 15-минутные проверки со статусом `IDLE` ошибочно переносили начало 60-минутного интервала, из-за чего реальный поиск мог не запускаться вообще.
- Теперь интервал отсчитывается только от последнего фактически завершённого цикла `FINISHED`.
- После исправления выполнен настоящий цикл: заявка поставлена в очередь и обработана, `unsafe_rows=0`.
- Swing-задания в БД включены и используют исполнитель `SWING_CLOSED_BAR_SEARCH_V1`; проверка новых H1/H4/D1 выполняется через единый DB-планировщик.
- Профильные тесты: 4 успешно.
- Перезапуск служб для этого исправления не требуется: оба исполнителя запускаются как новые одноразовые процессы по таймерам и читают обновлённый код при каждом запуске.

## Зафиксированная методология

- Порог готовности: 80 закрытых сделок на совместимую связку; порог не снижать.
- Точная связка: инструмент × стратегия × сторона × сессия × режим × правило выхода.
- Допустима иерархическая проверка: общая закономерность стратегии → инструмент и сторона → сессия, режим и выход.
- Объединять можно только заранее определённые совместимые контексты. Несовместимые сделки не смешивать.
- Архив формирует гипотезы и приоритеты; свежая когорта независимо подтверждает их.
- V3 и V4 не смешивать. Следующую когорту создавать только при изменении определения данных или режима.
- Реальные комиссии, bid/ask, спред, проскальзывание и ликвидность обязательны.
- Искусственный PASS запрещён.
- PF при отсутствии убытков показывать как «нет убытков / недостаточно данных», а не `999`.

## Правила допуска и риска

- LONG запрещён в подтверждённом нисходящем тренде без отдельной контртрендовой модели.
- SHORT запрещён в подтверждённом восходящем тренде без отдельной контртрендовой модели.
- При неизвестной стратегии, режиме или волатильности новый Paper-вход запрещён.
- `UNASSIGNED` хранить для аудита, но исключать из чистой когорты и OOS.
- Ожидаемое движение должно покрывать комиссию, спред и проскальзывание.
- Размер позиции рассчитывать от стопа и допустимого риска, а не фиксированного плеча.
- Лимитировать дневной убыток, просадку, общую экспозицию, риск инструмента и коррелированные ставки.
- Реальная торговля запрещена до строгого PASS всей цепочки.

## Архитектурные решения

- Акции и фьючерсы исследуются отдельными потоками и портфельными scope.
- Исследовательские позиции физически изолированы от текущего реального портфеля и старых когорт.
- Новые инструменты добавляются в активную вселенную только одной DB-транзакцией вместе с политикой стратегии и runtime-правилом.
- Система сама определяет приоритеты по перспективности, недозаполненности выборки, качеству данных и нагрузке сервера.
- Все планы, причины решений, заявки, прогресс, ошибки и результаты должны храниться в БД с единым `process_id`.
- Завершённые fingerprint и фолды повторно не считать; поиск должен быть checkpointed.

## Режим рынка

- Состояние определяется отдельно для каждого `инструмент × таймфрейм`.
- ATR считается по закрытым свечам.
- Тренд определяется по EMA/ADX либо нормализованному наклону доходности.
- Высокая/низкая волатильность определяется относительно собственной истории инструмента, например перцентилем ATR.
- Режим подтверждается несколькими закрытыми барами.
- Неопределённый режим — техническое отсутствие достаточного подтверждения, а не торговый режим.

## Известные незакрытые проблемы

1. Проверить, почему после 25.07 не формируются новые закрытые FRESH-сделки.
2. Проверить всю цепочку по одному новому `process_id` от котировки до записи закрытия и счётчика связки.
3. Проверить автоматическую постановку связки в OOS после достижения 80.
4. Сверить цифры UI с прямыми агрегатами БД и устранить кэш/устаревшие представления.
5. Проверить назначения стратегий и runtime-правила для всех активных акций и фьючерсов.
6. Проверить актуальные контракты, rollover и свежесть BR, NG, золота, юаня и доллара.
7. Проверить реальные bid/ask, глубину стакана и биржевую метку времени для активных OOS-инструментов.
8. Проверить, что статусы меняются по факту: `Ожидает → Выполняется → Готово/Ошибка`.

## Следующая проверка

1. Снять текущее состояние служб и последние ошибки.
2. Сверить максимальное время котировки, сигнала, Paper-заявки, позиции, закрытия и записи чистой когорты.
3. Выбрать один свежий сигнал и проследить его сквозной `process_id`.
4. Исправить первый найденный разрыв.
5. Получить минимум одно новое корректное закрытие в каждом активном потоке: акции и фьючерсы.
6. Проверить увеличение накопительного счётчика без создания новой несовместимой связки.
7. Подтвердить автоматическую OOS-заявку тестом на готовой связке.

## Проверка 28.07.2026 — разрыв до Paper-заявки

- Службы `finam-paper-pipeline`, `finam-paper-safe` и UI были активны.
- За последние 24 часа в БД найдено 986 сигналов; все имели итог `RISK_REJECTED`.
- Новых Paper-заявок, исполнений, позиций и закрытых сделок не было.
- Основные причины: `trend_flip_block` — 510, сессионный шлюз — 316,
  строгий runtime-шлюз — 159.
- Исправлена бесконечная блокировка смены режима: подтверждённый новый режим
  теперь сохраняется до раннего выхода.
- Runtime-шлюз теперь получает стратегию, таймфрейм и режим, а безопасное
  накопление доказательств разрешено только в изолированном Paper-режиме.
- Отрицательная expectancy, сессионные запреты, реальные сделки и критерии
  PASS этим изменением не обходятся.
- Проверки: компиляция модуля и 6 профильных тестов прошли успешно.
- Требуется перезапуск `finam-paper-pipeline.service`, после чего нужно
  подтвердить новое прохождение `сигнал → Paper-заявка → позиция → закрытие`.

## Правило обновления этого файла

## Проверка 28.07.2026, 18:50–19:20 МСК — восстановление Research Paper-контура

- Подтверждён корневой разрыв: `portfolio_scope` терялся перед общим entry gate, поэтому новая V5-когорта наследовала блокировки старых BR/NG/LKOH результатов.
- `FRESH_V5_CONFIRMED_EQUITY` и `FRESH_V5_CONFIRMED_FUTURES` теперь передаются в runtime-control; bootstrap новой изолированной когорты не наследует старый regime-control.
- После перезапуска служб новый BR-сигнал прошёл scope-bootstrap и создал Paper-fill. Реальное исполнение оставалось отключено.
- Одновременно выявлен и закрыт второй разрыв: глобальный directional gate отсутствовал на generic Paper-route. Теперь LONG при подтверждённом downtrend и SHORT при подтверждённом uptrend блокируются до PaperExecution, если DB-политика явно не разрешает контртренд.
- Два закрытия GAZP физически существуют в `closed_trades`, но корректно исключаются из чистой V5-когорты как LONG в подтверждённом downtrend.
- Materializer теперь сохраняет обязательные `regime_trend`, `regime_vol` и сторону входа для прозрачного аудита допуска.
- Экран `18080/workspace-v2` исправлен: отдельно показывает чистые и исключённые закрытия, открытые Paper-позиции, запрещённые направления и устаревшие контракты; ложное действие «ждать следующую сессию» удалено.
- Проверки: `TEST_ENTRY_GATE_PORTFOLIO_SCOPE_V1_OK`, `TEST_PAPER_CLOSED_TRADE_MATERIALIZER_V2_OK`, `TEST_GLOBAL_PAPER_DIRECTION_GATE_V1_OK`, `TEST_CONTROL_COMPACT_RESEARCH_STATUS_V1_OK`.
- Текущий безопасный режим: `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`; Paper Safe: `REAL_EXECUTION_ENABLED=0`.
- Требует проверки после перезапуска обновлённого UI: отображение новых карточек на `18080` и первое корректное режимно совместимое закрытие отдельно для акций и фьючерсов.
- Перезапуск 20:24:59 МСК подтверждён: `finam-paper-pipeline` PID 3482540, `marketcore-ui-shell` PID 3482542, обе службы active/running.
- `18080/workspace-v2` подтверждён после перезапуска: чистых V5 закрытий 0, исключённых 4, открытых Research Paper-позиций 1; BR downtrend/LONG помечен «Запрещено направлением», NGN6 — «Устаревший контракт».
- Прямое runtime-срабатывание нового directional gate пока ожидает следующий подходящий кандидат: BR сейчас блокируется раньше по `cluster_block:energy`, NG — по `ANTI_REENTRY_OPEN_POSITION`.
- В 20:07:01 МСК открыта изолированная V5 Paper-позиция NGQ6: BUY, `NG_CONSERVATIVE_BREAKOUT_M1`, контекст `range_normal_vol`; это не контртрендовая сделка.
- Найден разрыв restart recovery: после перезапуска `opened_at_ts` создавался заново по первой котировке, поэтому минимальное время удержания начиналось с нуля. Restore теперь берёт фактическое `created_at` из изолированного lifecycle позиции.
- Проверка restart recovery вместе с direction/scope gates: `4 passed`. Для применения исправления требуется перезапуск только `finam-paper-pipeline.service`, затем проверка закрытия текущей NG-позиции и её точной V5-классификации.
- Проверка после рестарта 20:32:14 МСК выявила вторичную перезапись времени: первый quote видел `last_qty=0` и снова считал восстановленную позицию новой (`age_sec=0.207`). Restore дополнен восстановлением `last_qty`; повторная группа тестов — `4 passed`. Требуется контрольный перезапуск pipeline.

После каждого существенного изменения обновлять:

- дату и источник проверки;
- подтверждённые цифры;
- что исправлено и чем проверено;
- текущий единственный приоритет;
- следующий безопасный шаг.

## Checkpoint 29.07.2026, 08:17 МСК — flat-only rollover и iPhone UI

- Добавлен автоматический rollover только для BR, NG и Gold: переключение разрешено лишь при отсутствии открытой Paper-позиции и после проверки свежести баров, спецификации стоимости и ликвидности текущего/следующего контракта.
- Переключение выполняется одной транзакцией, сохраняет исходный V5 scope и не создаёт заявок, исполнений или реальных сделок. BR runtime-контракт безопасно перечитывается pipeline только при flat-позиции.
- Планировщик `V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER` включён с интервалом 5 минут.
- Следующие контракты BRU6, NGU6 и GDZ6 добавлены только в watch/prewarm M1; они не включены в runtime-вселенную до успешного rollover.
- Фактическое решение в 08:16 МСК: BRQ6 → BRU6 заблокирован открытой позицией; NGQ6 → NGU6 заблокирован открытой позицией; GDU6 → GDZ6 заблокирован устаревшими барами следующего контракта. Переключений `0`.
- Компактный HOME адаптирован для iPhone: одна колонка, перенос длинного текста, полная ширина карточек и кнопка обновления высотой не менее 48 px. Исследовательские метрики и safety-логика не изменены.
- Проверки: Python compile успешно; профильный suite `20 passed`; SQL prewarm применён, три строки M1 включены.
- Safety подтверждена: `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`.
- Следующий шаг: дождаться свежих GDZ6-баров и закрытия текущих BR/NG Paper-позиций; rollover продолжит проверки автоматически. Для загрузки CSS и pipeline-кода требуется штатный restart соответствующих служб оператором.

## Checkpoint 29.07.2026, 08:32 МСК — fail-closed качество рыночных данных

- Добавлен центральный gate новых входов по качеству данных. Он использует только завершённые M1/M5-свечи, требует минимум три последовательных бара, ограничивает свежесть и блокирует разрывы временного ряда.
- Gate учитывает сессию инструмента: закрытый рынок имеет отдельный статус и не считается аварией. При любой ошибке проверки новый вход запрещён; EXIT, virtual stop и trailing продолжают сопровождать уже открытую позицию.
- Для фьючерсов новый вход дополнительно требует спецификацию комиссий не старше 48 часов. Backfill/replay не смешивается с live admission.
- Создано read-only представление `analytics.runtime_market_data_quality_v1`. Фактический срез в 08:29 МСК: `READY=4`, `STALE=8`, `OUT_OF_SESSION=4`; сомнительные инструменты не должны получать новые входы.
- HOME показывает одну короткую строку: `свежие N · задержка N · вне сессии N`; вне сессии не создаёт ложную тревогу.
- Добавлен часовой `CONTRACT_SPEC_SYNC_INTRADAY` по будням 06:30–23:30. Контрольный sync: 38 символов, 34 без изменений, 4 корректно пропущены, ошибок 0, runtime/исполнение не изменялись. `GDZ6` по-прежнему недоступен у источника и остаётся fail-closed.
- Профильные проверки нового контура: `14 passed`; расширенный набор дал 39 успешных и 2 старых несвязанных contract failure (порядок runtime-символов и субботняя session-политика).
- Safety подтверждена: `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`.
- Для загрузки pipeline gate и обновлённого HOME требуется штатный restart `finam-paper-pipeline.service` и `marketcore-ui-shell.service` оператором.

## Checkpoint 29.07.2026, 08:43 МСК — P&L в компактном HOME

- В каждой строке топ exact-веток рядом с прогрессом показан накопленный source-backed `P&L`, например `4 из 20 · P&L -0,66`.
- Значение берётся из `analytics.hierarchical_evidence_v1.net_pnl`; знак валюты не подставляется, чтобы не смешивать разные единицы инструментов.
- Исследовательская логика, ранжирование и safety не изменены. Проверки HOME/iPhone/data-quality: `12 passed`.
- Для отображения изменения требуется restart только `marketcore-ui-shell.service`.

## Checkpoint 29.07.2026, 08:55 МСК — нормализованный P&L в R

- Exact evidence расширен source-backed метриками `net_pnl_r`, `expectancy_r`, `r_observable`.
- R рассчитывается по каждой сделке как `net P&L / (|entry − первоначальный stop| × qty)`. Нулевое legacy-поле `realized_rr` не используется; при отсутствии исходного stop показатель считается ненаблюдаемым.
- Компактная строка HOME одновременно показывает `P&L net · P&L R · Exp/R · PF`. PF без наблюдаемых убытков отображается как `нет данных`, а не искусственное число.
- Штатный router самостоятельно перечитал код в 08:54 МСК. Лидирующая exact-ветка BR: `4/20`, `P&L net -0,662`, `P&L R -0,775`, `Exp/R -0,194`, `PF 0,00`.
- Проверки hierarchy/HOME/iPhone: `22 passed`; ручной запуск router и торговое исполнение не выполнялись.
- Для отображения изменения требуется restart только `marketcore-ui-shell.service`.

## Checkpoint 29.07.2026, 09:03 МСК — очистка scheduler и Swing UUID

- Семь legacy DB-заданий с исполнителями, отсутствующими в scheduler allowlist, точечно отключены и помечены `DISABLED_LEGACY_EXECUTOR_NOT_ALLOWED_V1`. Их определения сохранены для аудита; V5-задания не изменялись.
- После отключения новых failure по этим семи job нет (`0`). Повторяющийся шум с return code `126` остановлен.
- В `SWING_FUTURE_EXECUTION_V1` UUID результата и plan item явно преобразуются в строки перед передачей psycopg2; ошибка `can't adapt type UUID` устранена.
- Контрольный Swing research evaluator обработал 3 элемента: `items_evaluated=3`, `pass=0`, `live_allowed=0`, verdict `OK`. В БД записаны 3 OOS-результата; отсутствие PASS является исследовательским результатом, а не технической ошибкой.
- Проверки legacy-disable/Swing: `19 passed`; Python compile и SQL migration успешны.
- Safety подтверждена: `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`.

## Checkpoint 29.07.2026, 09:09 МСК — stale RUNNING reconciliation

- Исправлен общий lifecycle DB scheduler: после получения advisory lock он автоматически переводит осиротевшие `RUNNING` старше `timeout_seconds + 60` в `TIMEOUT` с return code `-2` и причиной `SCHEDULER_RESTART_STALE_RUNNING_RECONCILED`.
- Условие lock гарантирует, что активный scheduler не помечается stale; история run не удаляется.
- Зависшая запись `FORWARD_REMEDIATION_SCENARIOS` от 25.07 переведена в `TIMEOUT`; текущих `RUNNING` для job осталось `0`.
- Сам research executor проверен отдельно: `scenarios=0`, причина `FORWARD_REMEDIATION_NO_READINESS_DATA`, verdict `OK`. Stage 5 корректно находится в `WAITING/AWAITING_FORWARD_READINESS`.
- Профильные проверки scheduler/reconciliation: `8 passed`; торговое исполнение не запускалось.

## Аудит незакоммиченных изменений 28.07.2026

- Создана ветка `codex/research-edge-v5` от `50951c2ce1f20d8065a55707394708191e1f5b68` без изменения содержимого dirty tree.
- Рабочее дерево: 104 изменённых tracked-файла (`+5828/-767`) и более 80 новых файлов; в нём смешаны V2–V5, runtime, UI и локальные артефакты.
- AST-проверка 173 изменённых/новых Python-файлов прошла.
- Выделенный V5 research/Paper contract suite: `61 passed`.
- Полный suite имеет 45 известных падений; ещё один test-module не собирается из-за отсутствующего в venv `websockets`, хотя зависимость закреплена в `requirements.txt`.
- Полный dirty tree не признан эталоном и не закоммичен. Подробности: `UNCOMMITTED_AUDIT_V5.md`.
- Единственный приоритет: сформировать явный V5 manifest, отделить legacy/WIP и получить зелёную проверку manifest перед эталонным коммитом.
- V5 manifest сформирован из явного списка 95 файлов и проверен в отдельном checkout будущего git-индекса: `61 passed`.
- Проверка staged diff не выявила секретов или включения real execution; safety-конфигурация закрепляет `EXECUTION_ENABLED=0` и `REAL_EXECUTION_ENABLED=0`.
- Legacy/UI WIP и runtime-артефакты остаются вне manifest и вне эталонного коммита.

## Exit по состоянию свечей 28.07.2026

- Подтверждено первое чистое V5-закрытие: NGQ6, `range_normal_vol`, вход 20:07:01 МСК, выход 20:37:02 МСК, net PnL `+0.014536`.
- Устранено доминирование quote-driven time exit: `bars_held` теперь увеличивается только закрытой M1-свечой для BR/NG и M5-свечой для остальных инструментов.
- На каждом quote остаётся только проверка виртуального stop/trailing; stall/time оцениваются на событии закрытой свечи.
- Добавлен fail-closed regime-invalidation: LONG закрывается при подтверждённом свежем `CANDLE_REGIME_V3 down`, SHORT — при `up`.
- Energy time-exit переведён в аварийный предел 60 закрытых M1-баров (`ENERGY_MAX_BARS_IN_TRADE=60`).
- Paper trailing в dry-run сохраняет виртуальный stop в ExitEngine и больше не вызывает broker cancel/replace.
- NG direction policy lookup теперь может сопоставить стратегию `NG_CONSERVATIVE_BREAKOUT_M1` с DB timeframe M1, даже если quote intent имеет generic timeframe.
- Тестовое загрязнение `TEST@MISX` удалено строго из V5 projection/lifecycle: по обеим таблицам осталось 0 строк.
- Regression suite нового V5 exit-контура: `66 passed`.
- Runtime reload 21:00:21 МСК подтверждён: новый PID 3638452, Paper/real safety flags не изменились.
- BR восстановила фактический возраст позиции и получила первый persisted M1 bar (`raw_bars_held=1`); NG не получила бар до своего времени входа (`raw_bars_held=0`).
- Virtual trailing фактически применяется для BR и NG; после нового PID broker `missing_old_stop_order` больше не возникает.
- Исправлен второй trailing-route в `PositionLifecycleService` и добавлен persisted-regime fallback для websocket без trade progress.
- Повторные одинаковые virtual-stop решения теперь подавляются до event/DB/log записи по `TRAILING_ORDER_MIN_REPLACE_STEP`.
- Текущее чистое V5: 1 закрытие NG; открыты BR и новая NG Paper-позиции.
- Контрольный reload 21:02:56 показал, что локальный trailing cache мог теряться между двумя lifecycle routes: stop повторно записывался и мог уменьшаться. Источник истины исправлен на общий ExitEngine state; long stop теперь монотонный, повтор требует улучшения минимум на configured step. Проверки: `12 passed`; требуется reload.

## Нормализация V5 и Swing 28.07.2026

- Рабочее дерево `codex/research-edge-v5` очищено без потери WIP.
- Проверенные добавления закреплены атомарно: master-context/hygiene (`d8e37ff6`), полный risk schema (`3def889f`), candle-driven swing research (`1b781d7c`) и правильный приоритет adaptive entry constraints (`810cb2cb`).
- Swing использует только закрытые H1/H4/D1-бары; Paper и validation разделяют `dynamic_exit_v1`. Основные выходы: ATR stop/trailing, исчезновение тренда и volatility risk; `MAX_HOLD` — страховка.
- Финальный объединённый Swing/Risk acceptance: `47 passed`; master-context verifier OK.
- Непроверенный research/UI слой сохранён на ветке `codex/quarantine-pre-v5-wip-20260728`, commit `f91941a7`; он не является частью canonical V5.
- Расширенный quarantine suite: 69 passed, 5 contract failures; atomic-policy branch дополнительно имеет 5 незавершённых runtime assertions. Эти ветки не допущены в V5.
- Runtime snapshots восстановлены к HEAD; backup/log перенесены в `/tmp/finam-core-local-archive-20260728`.
- Службы, scheduler, миграции и торговое исполнение при нормализации не запускались.

## Canonical Intraday V5 28.07.2026

- Intraday сохранён как обязательный отдельный V5-контур и не заменён swing-логикой.
- Clock: закрытые M1 для BR/NG, закрытые M5 для остальных инструментов.
- Выходы: virtual stop/trailing на quote; regime invalidation и safety hold — только по завершённым configured bars.
- Restart restore, portfolio scope, directional fail-closed gate, materialization и clean/excluded attribution входят в baseline.
- Acceptance на чистом canonical HEAD: `34 passed`.
- Службы и runtime не запускались; применение последнего monotonic trailing commit после reload требует фактической проверки.

## Runtime checkpoint 21:27–21:30 МСК

- Pipeline reload применён: PID `3754387`, active; Paper Safe active.
- Safety подтверждена: `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`, trailing dry-run включён.
- Restart closed-bar fix загружен. Read-only расчёт тем же контрактом БД восстанавливает для открытой NGQ6 `30` завершённых M1-баров после входа, а не `1`.
- Runtime-подтверждение в памяти пока невозможно: после restart не пришёл `MD_FIRST_QUOTE`; watchdog в 21:29:28 выполнил reconnect, но поток снова остановился на `MD_SUBSCRIBE_OPENED`.
- Отдельно подтверждён data-ingestion blocker: несуществующий `2xEQT@MISX` после шести retry завершает весь timeframe step ошибкой. Требуется fail-isolation инструмента.
- `TEST@MISX` удалён из projection/lifecycle, verified `0/0`.

## Runtime checkpoint 21:34–21:35 МСК

- Исправленный pipeline загружен: PID `3770551`; первая котировка BRQ6 пришла в 21:34:11 без ожидания watchdog.
- NGQ6 успешно восстановлена из projection: `old_qty=0`, `projection_qty=1`; placeholder error отсутствует, ExitEngine выполняет HOLD.
- Persisted closed-bar reconstruction перед restore даёт `30` завершённых M1 после входа; reset bar-clock до `1` устранён.
- Safety без изменений: Paper mode, execution/real trading disabled, trailing dry-run.
- Ingestion fail-isolation подтверждён: `2xEQT@MISX` остановлен после первого `NOT_FOUND` как `SECURITY_NOT_FOUND`, после чего обработка продолжилась по следующим символам; BRQ6 M1 успешно обновлён.
- Monotonic trailing code загружен, но нового улучшения virtual stop после этого reload ещё не было; runtime monotonic event требует наблюдения.

## Runtime checkpoint 21:36–21:37 МСК

- После операторских restart все четыре службы active: pipeline PID `3782708`, bars ingestion PID `3783032`, Paper Safe и UI.
- Первая котировка пришла в 21:36:44; NGQ6 восстановилась из projection без SQL errors.
- В 21:37:03 NGQ6 закрыта по состоянию свечей: `regime_invalidation_long`; exit payload содержит восстановленный `bars_held=40`, а не reset `1`.
- Closing Paper fill: SELL 1 @ `2.71675`, `FRESH_V5_CONFIRMED_FUTURES`; materialization в `closed_trades` асинхронно ожидается.
- В 21:37:18 открыта новая BRQ6 Paper LONG @ `84.1825`; virtual stop `83.77` применён с `dry_run=1`.
- После нового PID нет `missing_old_stop` и broker trailing route. `TEST@MISX` остаётся `0/0`.

Не записывать предположения как факты. Непроверенные сведения помечать словами «требует проверки».

## V5 hierarchical evidence runtime 28.07.2026, 22:45–22:51 МСК

- Migration 215 применена; `scope_code` и `timeframe_code` физически присутствуют.
- Первый router-run завершён с `VERDICT=V5_HIERARCHICAL_EVIDENCE_ROUTER_V1_OK`:
  18 groups — STRATEGY 3, INSTRUMENT_SIDE 4, COMPATIBLE_CONTEXT 5, EXACT_CONTEXT 6.
- Все группы при текущих 9 clean trades имеют `DISCOVERY_ONLY`; early stop=0,
  READY_FOR_OOS=0. Максимум: 5 trades на верхних уровнях, 4 на exact.
- Runtime-аудит выявил и исправил transport marker `timeframe=LIVE`: evidence
  теперь использует canonical clock BR/NG M1 и equities M5. LIVE/UNKNOWN rows=0.
- UI PID после reload active; document `VERIFIED`, hierarchy отображается без
  новых кнопок; nearest exact: BRQ6 breakout, 4/80, DISCOVERY_ONLY.
- Safety не менялась: runtime/execution/orders/fills changed=0, live_allowed=0;
  Paper execution flags остаются disabled.
- Проверки после data-lineage fix: 13 passed; router повторно выполнен успешно.
- Verdict: `V5_HIERARCHICAL_EVIDENCE_RUNTIME_VERIFIED`.

## V5 accumulation checkpoint 29.07.2026, 06:12 МСК

- Все ключевые units active: `finam-v5-bars-fast.timer`,
  `finam-market-bars-ingestion.service`, `finam-paper-pipeline.service`,
  `finam-paper-safe.service`, `marketcore-ui-shell.service`.
- Control Center quality `VERIFIED`; autonomous research mode enabled.
- Safety подтверждена: `EXECUTION_MODE=paper`, `EXECUTION_ENABLED=0`,
  `REAL_TRADING_ENABLED=0`, `TRAILING_ORDER_DRY_RUN=1`.
- Чистая когорта `FRESH_V5_CONFIRM`: 11 закрытых сделок, суммарный net PnL
  `-0.24490380000000403`; последнее закрытие — 28.07.2026 23:13 МСК.
- Открыто 6 изолированных Paper-позиций: NVTK, NGQ6, BRQ6, VTBR, LKOH, GAZP.
- Hierarchical evidence: Strategy 3 groups (max 5), Instrument/Side 4 (max 5),
  Compatible Context 6 (max 4), Exact Context 7 (max 4).
- Максимальная exact-ветка: BRQ6 M1 breakout long / off-main /
  range-normal / regime-invalidation — 4 сделки, expectancy `-0.165429375`,
  observable PF `0`, решение `DISCOVERY_ONLY`.
- `READY_FOR_OOS=0`; первая контрольная граница 20 exact trades ещё не достигнута.
- UI `closed=0` означает закрытия за последний час; полный clean V5 sample равен 11.
- Ночной raw wall-clock age M1/M5 превышает дневные freshness thresholds из-за
  отсутствия новых закрытых баров вне активной сессии; units остаются active.
- Git: branch `codex/research-edge-v5`, HEAD
  `08ef6b274be6521e78049d22bb223391db4c8a9c`; до сохранения checkpoint tree clean.
- Текущий приоритет: автономно накопить первую exact-ветку до 20 закрытий,
  затем оценить expectancy/PF и решение router без ослабления OOS-порога 80.

## Evidence-driven acceleration 29.07.2026

- Приоритет router больше не равен простому числу сделок: exact-ветки ранжируются
  по стоимости следующего полезного наблюдения — 20–79, 10–19, 5–9, 3–4,
  затем новые ветки. `EARLY_STOP` получает отрицательный score.
- Supporting hierarchy оставлена для анализа, но её score ограничен и она больше
  не может вытеснить exact-контекст из runtime universe.
- Миграция `216_v5_evidence_driven_runtime_priority_v1.sql` применена; runtime-view
  читает только `FRESH_V5_CONFIRM` + `EXACT_CONTEXT` и исключает `EARLY_STOP`.
- Router пересобран без изменения runtime/execution/orders/fills. Фактический
  приоритет: BRQ6 4 trades = 304; NGQ6 2 trades = 102; NVTK/VTBR 1 trade = 101.
- Control Center дополнен read-only диагностикой каждой открытой Paper-позиции:
  стратегия, qty, возраст в завершённых барах и состояние candle-exit monitor.
- Runtime read-only проверка: BRQ6 31 M1, NGQ6 25 M1, VTBR 11 M5, NVTK 3 M5;
  GAZP/LKOH ожидают первый завершённый M5 после точки восстановления.
- UI сохраняет минимальное управление: диагностическая секция не добавляет кнопок.
- 24 профильных теста и server-side render прошли; документ `VERIFIED`.
- Для загрузки нового UI-кода требуется операторский
  `sudo systemctl restart marketcore-ui-shell.service`; автоматический restart
  не выполнен, потому что sudo требует интерактивный пароль.
- Safety и пороги не ослаблены: real execution запрещён, early-stop = 20,
  OOS = 80 exact trades.
- Первый UI reload в 06:26 выявил state-dependent validation error: при уже
  активном edge-job отключённая RUN-команда не имела обязательного
  `blocked_reason_code`. Команда теперь получает
  `RESEARCH_COMMAND_ALREADY_ACTIVE`; текущий DB-state render снова `VERIFIED`.
- Повторный UI reload подтверждён в 06:29:01 МСК: HTTP quality `VERIFIED`, секция
  open-position diagnostics и возраст в закрытых барах видимы; ровно две
  research-команды, broker/live-команд 0. Safety flags без изменений.

## Compact Edge UI 29.07.2026

- Главный экран сокращён с 8 карточек и 9 крупных секций до 5 карточек,
  top-5 exact-веток, компактных открытых позиций, одной строки состояния и одной
  видимой кнопки `Обновить`.
- RUN удалён только из main render; governed backend и автономный scheduler не
  изменены. Если оператор ничего не нажимает, накопление продолжается.
- Jobs, raw freshness, hierarchy levels, archive plan и раздельные scope-таблицы
  больше не рендерятся на главной, но остаются в read model/API для диагностики.
- Exact-таблица показывает ветку, прогресс 20/80, expectancy/PF и решение router.
- Текущий DB-state render: `VERIFIED`, top exact rows 5, open positions 6,
  visible commands: refresh 1 / run 0; visible technical sections 0.
- 35 профильных тестов прошли. Safety без изменений: Paper only, execution/real
  trading disabled, trailing dry-run. Требуется UI-only reload.
- UI reload подтверждён в 06:46:06 МСК: HTTP `VERIFIED`, cards 5, exact rows 5,
  open-position section present, единственная команда `RESEARCH.REQUEST_REFRESH`,
  technical sections 0. Compact Edge UI полностью загружен.

## V5 hierarchical evidence router 28.07.2026, 22:38–22:47 МСК

- Реализованы четыре изолированных уровня evidence: STRATEGY (scope × timeframe ×
  strategy × side), INSTRUMENT_SIDE, COMPATIBLE_CONTEXT и EXACT_CONTEXT.
- Equity/futures scopes и разные timeframes физически не объединяются. V3/V4 не
  участвуют: источник только `closed_trades_fresh_v5_confirmed`.
- Совместимые session/regime группы берутся из versioned compatibility table;
  точный уровень сохраняет фактические session, regime и exit rule.
- Иерархические уровни используются для collection priority/early stop, но не
  дают PASS. `READY_FOR_OOS` возможен только EXACT_CONTEXT при >=80 trades,
  observable PF >=1.15, positive net expectancy и cost buffer 1.5x.
- Scheduler allowlist получил реальный `HIERARCHICAL_EVIDENCE_ROUTER_V1` executor;
  Control Center показывает четыре уровня, stop/OOS и nearest exact branch без
  добавления кнопок.
- Проверки: compile, 17 focused tests, `git diff --check`.
- Deployment pending: применить migration 215, один раз выполнить router, проверить
  строки V5 и затем restart только UI. До этого runtime status требует проверки.

## V5 fast bars runtime verification 28.07.2026, 22:34–22:36 МСК

- `finam-v5-bars-fast.timer` installed, enabled и active/waiting.
- Два последовательных автоматических oneshot cycle завершились успешно; каждый
  обработал ровно 7/7 exact targets, без retry и без overlap.
- Первый цикл занял около 9 секунд; exit status 0/SUCCESS.
- После второго цикла фактический age: пять M1 series — `120` секунд, две M5
  series — `360` секунд. Предыдущее M1 значение `226` секунд устранено.
- Fast timer не меняет pipeline/execution; Paper safety остаётся
  `EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`, trailing dry-run.
- Verdict: `V5_FAST_BARS_REFRESH_RUNTIME_VERIFIED`.

## V5 fast bars refresh 28.07.2026, 22:18–22:23 МСК

- Для устранения M1 age 226 sec подготовлен независимый fast refresh, не зависящий
  от длительности полного scout-universe cycle.
- Exact targets: BRQ6/NGQ6/SBER/GAZP/LKOH M1 и NVTK/VTBR M5; cross-product
  timeframes исключён новым параметром `--targets symbol=timeframe`.
- `finam-v5-bars-fast.service` — research-only oneshot с timeout 15 sec на target
  и общим 120 sec; timer использует `OnUnitInactiveSec=60`, поэтому экземпляры
  одного fast service не перекрываются.
- Проверки: Python compile, 7 tests, `systemd-analyze verify`, `git diff --check`.
- Units ещё не установлены в `/etc/systemd/system`; runtime freshness после timer
  требует операторской установки/старта и отдельного наблюдения минимум 2 цикла.

## V5 Edge Control UI runtime 28.07.2026, 22:15–22:17 МСК

- UI reload применён: `marketcore-ui-shell` PID `3955695`, active/running.
- HTTP render подтверждён: document `operator.control_center.v2`, quality `VERIFIED`.
- В обычном состоянии отображаются ровно две команды: governed manual edge RUN
  и research REFRESH. Autonomous mode отображается как `Включён`.
- Sections scheduler, V5 freshness и edge control присутствуют. Broker/live/micro-live
  command codes в документе отсутствуют; Paper safety flags не менялись.
- На runtime-замере age закрытых свечей: M1 `226` секунд, M5 `346` секунд.
  M5 находится в установленном допуске 420 секунд; M1 превышает цель 180 секунд.
- Следующий data-plane приоритет: отделить короткий V5 refresh subcycle от полного
  scout universe, чтобы длительные второстепенные запросы не задерживали новый цикл.

## V5 Edge Control read model 28.07.2026, 22:09–22:16 МСК

- Compact Control V3 закреплён в canonical domain producer registry; будущий
  restart UI больше не вернёт старый Control Center V2.
- Единый read model теперь включает: состояние autonomous scheduler, последние
  jobs, governed command queue, текущий edge process, свежесть семи приоритетных
  V5 series, чистые futures/equity сделки и OOS readiness.
- UI оставляет минимальный набор управления: одна контекстная основная кнопка
  (`RUN` либо `CANCEL MANUAL PENDING`) и одна кнопка refresh.
- Если оператор ничего не нажимает, autonomous edge search продолжает работать.
  Ручной RUN только добавляет внеочередной governed request; CANCEL ограничен
  pending-запросами того же оператора и не может отменить `system.scheduler`.
- Full server-side render: `operator.control_center.v2`, quality `VERIFIED`;
  freshness и scheduler sections присутствуют; в обычном состоянии две команды.
- Проверки нового контура и governed worker: 8 passed. Два ранее известных
  Research/Home contract tests остаются отдельным долгом: progress/trusted source.
- Требуется restart только `marketcore-ui-shell.service`, затем HTTP/UI verification.

## Auto-edge/UI audit 28.07.2026, 22:02–22:08 МСК

- Автоматический edge-контур уже имеет autorun, governed command worker,
  market-universe queue, checkpointed walk-forward/OOS и команды UI run/cancel.
- Подтверждён operational blocker: DB schedule содержит неподдерживаемый executor
  `HIERARCHICAL_EVIDENCE_ROUTER_V1`, из-за которого общий scheduler прерывал все
  последующие research jobs и `finam-market-universe-research-queue.service` падал.
- Scheduler оставлен fail-closed по allowlist, но ошибка неизвестного executor
  теперь сохраняется в job run/failure rollup и изолируется от остальных jobs.
- Runtime подтверждение: scheduler больше не завершился на router и перешёл к
  разрешённому `SESSION_EXECUTION_EDGE_V2`. Пять профильных тестов прошли.
- UI-аудит: Research API отдаёт run/search/universe actions, однако основной
  Control Center не показывает run/cancel, часть отображаемых actions не имеет
  governed handler, прогресс edge search и trusted walk-forward источник не
  полностью отражены. Статус UI пока `PARTIAL_CONTROL`, не production-complete.
- Следующий этап: единый V5 Edge Control read model с состоянием scheduler,
  очереди, текущего процесса, свежести, кандидатов/OOS/Paper evidence и только
  allowlisted Paper/Research-командами. Live promotion остаётся запрещённым.

## Freshness checkpoint 28.07.2026, 21:52–21:57 МСК

- Все четыре runtime-службы подтверждены как `active`; real execution остаётся
  выключено (`EXECUTION_ENABLED=0`, `REAL_TRADING_ENABLED=0`), trailing — dry-run.
- Подтверждён дефект расписания continuous bars ingestion: включённый universe
  содержит 68 точных пар `symbol × timeframe` (64 M1, 4 M5), но процесс ошибочно
  выполнял все 68 символов для M1, M5 и H1, создавая до 204 последовательных шагов.
- Планировщик исправлен: DB timeframe теперь соблюдается, а идентификаторы без MIC
  (`BTCUSD`, `ETHUSD`) пропускаются до Finam API без шести бесполезных retry.
- Новый план проверен фактически: 68 targets, 66 valid, 2 `MISSING_MIC`.
- Проверки: 3 профильных теста, Python compilation и `git diff --check` прошли.
- Изменение ещё не загружено в процесс: ingestion PID `3783032` работает с
  21:36:49 МСК; автоматический restart заблокирован требованием sudo-пароля.
- Следующий безопасный шаг: операторский restart только
  `finam-market-bars-ingestion.service`, затем подтвердить длительность полного
  цикла и свежесть V5 M1/M5. Pipeline перезапускать не требуется.

## Freshness runtime verification 28.07.2026, 21:57–22:00 МСК

- Финальная версия загружена: ingestion PID `3878185`, active/running с 21:57:46.
- Первые семь успешных шагов цикла подтверждены в целевом порядке: BRQ6 M1,
  NGQ6 M1, SBER M1, GAZP M1, LKOH M1, NVTK M5, VTBR M5.
- Фактическая свежесть на замере: все пять M1-инструментов — около 137 секунд;
  оба M5-инструмента — около 197 секунд. Это соответствует закрытым свечам.
- После приоритетной V5-когорты цикл продолжает широкий research/scout universe;
  задержки второстепенных инструментов больше не блокируют свежесть V5.
- Safety подтверждена без изменений: Paper mode, execution/real trading disabled,
  trailing dry-run. Чистое накопление V5 активно.

## V5 USD / Gold / CNY branches prepared 29.07.2026

- Prepared 12 isolated branches: USD perpetual, dated Gold and CNY perpetual,
  each as M1/M5 × LONG/SHORT. BR/NG evidence remains in its existing scope.
- Asset-specific volatility gates use each instrument's own ATR percentile.
  Existing cost, session and direction guards remain mandatory; candle-state and
  symmetric trailing exits use the selected M1/M5 closed-bar clock.
- USD/CNY funding and Gold rollover lineage are explicit OOS blockers.
- Compact UI source adds a button-free `Валюты и золото` section with direction
  progress, active timeframe, fees/spread and funding/rollover status. CNY TOD/TOM
  remain display-only controls marked `DATA/COST NOT READY`.
- Validation: 41 focused tests, source compilation and diff checks passed.
- Deployment awaits an owner-level DB migration: the `alex` attempt rolled back
  atomically because the canonical resolver is owned by `postgres`.
- Safety unchanged: Paper mode, execution/real trading disabled, trailing dry-run.
- Post-deploy audit found the first flat-only M5→M1 rotation correctly blocked by
  active-universe governance because only M5 strategy policies existed. Migration
  217 now clones the governed policy for M1; no fills, orders or positions changed.

## Plain-Russian operator UI 29.07.2026

- Main Control labels now explain system activity for a non-professional user:
  completed examples, purchases/sales, current observation clock, trading costs,
  daily carry, contract transition and the reason independent validation is blocked.
- English research shorthand (edge, Paper, LONG/SHORT, OOS, funding, rollover,
  fee/spread and exact) is removed from the rendered primary page.
- No controls were added; Refresh remains the only button. Autonomous behavior and
  all execution safety settings are unchanged. Validation: 26 focused tests passed.

## Compact Russian UI follow-up 29.07.2026

- Multi-asset display reduced from six verbose rows to three short asset rows.
- Each row now shows only active minutes, M1/M5 purchase/sale counts and cost status.
- Priority table reduced to instrument, direction and sample progress; long inline
  explanations and professional performance abbreviations were removed.
- No behavior or controls changed. Validation: 26 focused tests passed.

## Current-only operator actions 29.07.2026

- The one-minute operator-decision refresh timer is active and healthy.
- Home UI now excludes source-stale historical decisions while retaining them in
  the database and lineage audit. Expired decisions whose source is still current
  remain visible and disabled according to the existing lifecycle policy.

## Three-section compact HOME 29.07.2026

- Canonical HOME now uses a dedicated compact renderer backed by the verified V5
  read model. The page contains only `Сейчас`, `Прогресс`, and `Нужно внимание`.
- The main page has nine short metric rows and one governed Refresh command.
  Technical tables, historical actions, strategy codes and performance shorthand
  are no longer rendered on HOME.
- Attention is based only on the current edge process and actual bar freshness;
  the historical 24-hour failure counter is intentionally excluded.
- The previous detailed HOME renderer remains available in source and retains
  direct regression coverage as a legacy presentation contract.
- No research, schedule, scope, execution or safety behavior changed. Validation:
  43 focused tests passed.

## Contract specification sync recovery 29.07.2026

- Repeated edge cycles stopped at `SYNC_CONTRACT_SPECS` because four historical
  `-RM` foreign-share symbols no longer have an executable MOEX reference.
- These symbols are now audited as `SKIPPED / MOEX_FOREIGN_SHARE_REFERENCE_UNAVAILABLE`
  instead of failing the complete specification refresh. Active Russian equities
  without TQBR data still fail closed.
- Runtime verification: 38 symbols processed, 34 unchanged, 4 skipped, 0 failed,
  sync status `SUCCEEDED`, return code 0. No execution state changed.
- Validation: 46 focused tests passed. Paper safety remains unchanged.

## Compact HOME browser rendering fix 29.07.2026

- HOME API contained all three sections, but the browser removed `Сейчас` and
  `Прогресс` because their metric rows were not wrapped in the required
  RenderTree `metric_list` container.
- Both sections now use the canonical container and have a regression test for
  browser empty-section cleanup. Research logic and safety are unchanged.

## Compact universe coverage line 29.07.2026

- HOME progress now states the dynamic active-universe count, how many instruments
  already have clean closed V5 examples, and how many leaders are shown.
- Counts are source-backed and not hard-coded; research behavior is unchanged.

## Russian instrument labels 29.07.2026

- Compact HOME progress uses the Russian instrument-reference name and keeps the
  exchange ticker in parentheses for unambiguous identification.
- A small presentation fallback covers active Russian shares whose reference name
  is still equal to the raw symbol. Research data and routing are unchanged.

## Runtime/UI synchronization checkpoint 29.07.2026 15:15 MSK

- Active market-bar refresh covers the complete enabled M5 universe; HOME reports
  16 fresh instruments with zero stale rows during the verified session.
- USD, CNY and Gold are included in the microstructure subscription priority list.
  A missing SELECT privilege on `analytics.market_contract_cost_spec_v1` for the
  `finam` role was corrected; the next eligible CNY trend-up signal passed the cost
  gate and produced a Paper fill at 14:00:36 MSK.
- V5 progress is aggregated by instrument and direction instead of exposing one
  exact-context bucket as though it were the instrument total. Verified leaders
  changed from misleading 4/2/2 to BR 6, NG 4 and NVTK 4; HOME also reports the
  current daily V5 count.
- HOME contains separate collapsible Equity and Futures trade tables. Both support
  header sorting and show Russian labels, LONG/SHORT, entry, closed exit price or
  signed current P&L in the exit column, holding time, reason, state and RUB P&L.
- Trailing-order source supports BR/NG LONG and SHORT. It remains Paper dry-run;
  LIVE and real execution remain disabled.
- Deferred: `RANGE_BOUNDARY_SHADOW_V1`; operator-confirmed soft TIME_EXIT with a
  hard fail-safe; audited Paper close/modify commands and UI controls; further HOME
  mark-to-market query optimization.
### Runtime recovery and UI correction — 29.07.2026 18:10 MSK

- PAPER pipeline restored from Git HEAD after an incomplete file transfer; remote `py_compile` passes, service is `active`, PID `2973679`.
- PAPER `TIME_EXIT` now requires explicit per-symbol operator approval; stop-loss and trailing exits remain automatic.
- Home render route verified independently: HTTP 200, document `operator.home.v2`.
- Progress view expanded from top-3 to top-5.
- Active position rows use supported `RenderNodeStateV2(status_code="ACTIVE")` and receive a distinct background.
- Obsolete Back/Home buttons are hidden in the workspace shell.
- UI service must be restarted after deployment so the running Python process reloads the corrected renderer.
### Adaptive Brent Paper risk — 29.07.2026 20:33 MSK

- Enabled for both LONG and SHORT in Paper only.
- Structural stop is clamped to 1.8–2.5 ATR with a 0.25 ATR level buffer.
- Target is at least 2.5 ATR and at least 1.5R.
- Entry requires current M5 volume >= 1.3x median of the previous 20 positive-volume M5 bars.
- Weak or warming-up volume blocks a new adaptive BR entry; it never widens risk to force a trade.
- Paper restarted successfully: active PID 3840830 since 20:31:43 MSK; remote compile passed and no startup traceback was observed.
- Existing BR position remains open and anti-reentry blocks duplicate exposure; adaptive settings apply to the next new BR entry.
### Multi-futures adaptive Paper policy — 29.07.2026 20:41 MSK

- Added a shared pure `FuturesAdaptiveRiskPolicy` for BR, NG, USD, CNY and GOLD, with mirrored LONG/SHORT geometry.
- BR runs in ENFORCE: 1.8–2.5 ATR structural stop, target >=2.5 ATR and >=1.5R.
- NG runs in SHADOW: 1.5–2.2 ATR stop, 3.0 ATR target, >=1.7R, volume threshold 1.5x; risk-normalized qty is about 0.533 of the old 0.8 ATR reference.
- USD runs in SHADOW: 1.2–1.8 ATR stop, 2.2 ATR target, >=1.5R; existing strict cost/funding gate remains authoritative.
- CNY runs in SHADOW: 1.2–1.7 ATR stop, 2.0 ATR target, >=1.5R; runtime telemetry confirmed.
- GOLD runs in SHADOW: 1.8–2.5 ATR stop, 3.5 ATR target, >=1.8R; dated-contract rollover controls remain authoritative.
- Every profile rejects a candidate recommendation when target movement does not cover explicit round-trip costs by at least 3x.
- REAL execution is untouched. Runtime active after restart: PID 3877920 since 20:39:55 MSK; BR/NG/CNY telemetry observed without import or startup errors.
### Daily futures risk calibrator — 29.07.2026 20:58 MSK

- Added an advisory-only daily calibrator for BR/NG/USD/CNY/GOLD, split by LONG/SHORT.
- Source is restricted to `trade_source='paper'` and `payload.context.cohort LIKE 'FRESH_V5%'`; legacy-derived trades are excluded.
- MAE/MFE are reconstructed from M1/M5 market bars; zero placeholder fields in `closed_trades` are not trusted.
- ATR is reconstructed from the 14 completed bars available at entry; entry volume is normalized to the prior 20-bar median.
- Recommendation requires at least 20 valid paths and 8 profitable trades. At 50 paths status becomes `CANDIDATE_FOR_REVIEW`; nothing is applied automatically.
- First trusted run: BR LONG 8/3 winners; NG LONG 5/1; NG SHORT 1/0; CNY LONG 1/0; other direction/asset buckets 0. All correctly remain `INSUFFICIENT_DATA` with no recommended values.
- Results are stored in `analytics.futures_risk_calibration_v1`; unit tests pass.
- Timer definition runs daily at 21:15 Europe/Moscow with a persistent two-minute randomized delay; system installation requires operator sudo.
### Automated futures Shadow-to-Paper promotion — 29.07.2026 21:12 MSK

- Added conservative paired Shadow lifecycle reconstruction for every trusted FRESH_V5 Paper close.
- Same entry/horizon are used; if stop and take are touched in one bar, stop wins to prevent optimistic bias.
- Promotion requires >=80 paired trades, >=20 OOS, shadow expectancy >= baseline +0.10R, positive shadow/OOS expectancy, drawdown not worse, OOS improvement, and largest-win concentration <=35%.
- Auto-promotion writes a versioned `ACTIVE` profile for execution_mode=paper only. REAL is excluded and still requires operator approval through future REAL_DRY_RUN/REAL_MICRO workflow.
- Paper runtime reads only ACTIVE Paper profiles with a 5-minute cache and falls back to built-in parameters on any DB error.
- Every Paper futures intent records `risk_profile_version` and source, keeping V5 evidence attributable across promotions/rollbacks.
- Shadow pairs are stored separately and never increment V5 trade counters.
- First run: BR LONG 8 pairs/OOS 1; NG LONG 5/1; NG SHORT 1/0; CNY LONG 1/0; all promotion guards correctly blocked.
- Five tests passed; no runtime profile was activated.
