BEGIN;

INSERT INTO presentation.ui_resource_v1
    (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
    ('research.validation_funnel.title','ru','Воронка проверки','Воронка проверки','Проверка','Число вариантов, последовательно прошедших каждый этап проверки.','','research'),
    ('research.tile.validation_in_sample','ru','In-sample','Обучение','Обуч.','Положительный результат на обучающем историческом участке до отбора OOS.','','research'),
    ('research.tile.validation_oos','ru','OOS','OOS','OOS','Результат сохранился на независимых исторических данных до торговых издержек.','','research'),
    ('research.tile.validation_after_costs','ru','После издержек','После издержек','Издержки','Положительное ожидание и Profit Factor сохранились после комиссий, спреда и проскальзывания.','','research'),
    ('research.tile.validation_stable','ru','Устойчивость','Устойчивость','Устойчив.','Результат устойчив по временным фолдам и прошёл финальный holdout.','','research')
    ,('research.validation_funnel.recommendation.title','ru','Главная потеря','Главная потеря','Потеря','Этап с максимальным сокращением числа вариантов и рекомендуемое системное решение.','','research')
    ,('research.validation_funnel.stage','ru','Этап','Этап','Этап','Этап максимальной потери вариантов.','','research')
    ,('research.validation_funnel.lost','ru','Потеряно','Потеряно','Потеря','Сколько вариантов отсеялось на этом этапе.','','research')
    ,('research.validation_funnel.solution','ru','Решение','Решение','Решение','Сценарий, который система применит при генерации следующего исследования.','','research')
    ,('research.funnel.stage.in_sample','ru','Обучение','Обучение','Обуч.','Максимальная потеря произошла на обучающей выборке.','','research')
    ,('research.funnel.stage.oos','ru','OOS','OOS','OOS','Максимальная потеря произошла на независимых исторических данных.','','research')
    ,('research.funnel.stage.after_costs','ru','Издержки','Издержки','Издержки','Максимальная потеря произошла после учёта торговых издержек.','','research')
    ,('research.funnel.stage.stability','ru','Устойчивость','Устойчивость','Устойчив.','Максимальная потеря произошла на проверке устойчивости.','','research')
    ,('research.funnel.recommendation.reframe_entry','ru','Новые входы','Новые входы','Входы','Система создаст новые экономически обоснованные условия входа вместо расширения прежней сетки.','','research')
    ,('research.funnel.recommendation.reduce_overfit','ru','Снизить переобучение','Меньше параметров','Параметры','Система сократит число параметров и расширит проверяемые рыночные режимы.','','research')
    ,('research.funnel.recommendation.reduce_turnover','ru','Снизить оборот','Снизить оборот','Оборот','Система создаст варианты с меньшей частотой сделок и лучшей исполнимостью.','','research')
    ,('research.funnel.recommendation.expand_evidence','ru','Расширить выборку','Больше данных','Данные','Система расширит число временных фолдов и режимов без ослабления PASS.','','research')
    ,('research.degradation.title','ru','Деградация стратегий','Деградация','Деградация','Критерии потери качества и необходимость исследовательского карантина.','','research')
    ,('research.degradation.column.strategy','ru','Стратегия','Стратегия','Стратегия','','','column')
    ,('research.degradation.column.symbol','ru','Инструмент','Инструмент','Инстр.','','','column')
    ,('research.degradation.column.oos','ru','OOS, %','OOS, %','OOS','','','column')
    ,('research.degradation.column.costs','ru','Издержки, %','Издержки, %','Издержки','','','column')
    ,('research.degradation.column.stability','ru','Устойчив., %','Устойчив., %','Уст.','','','column')
    ,('research.degradation.column.cycles','ru','Циклы','Циклы','Циклы','','','column')
    ,('research.degradation.column.status','ru','Деградация','Деградация','Статус','','','column')
    ,('research.degradation.column.block','ru','Блокировка','Блокировка','Блок','','','column')
    ,('research.degradation.status.healthy','ru','Норма','Норма','Норма','Деградация не подтверждена.','','research')
    ,('research.degradation.status.no_in_sample_edge','ru','Нет основы','Нет основы','Нет','Даже обучающая выборка не показывает экономического преимущества.','','research')
    ,('research.degradation.status.oos_collapse','ru','OOS-провал','OOS-провал','OOS','Менее 20% обучающих вариантов сохраняются на OOS.','','research')
    ,('research.degradation.status.cost_erosion','ru','Съели издержки','Издержки','Издержки','После издержек сохраняется менее 50% OOS-вариантов.','','research')
    ,('research.degradation.status.unstable','ru','Нестабильно','Нестабильно','Нестаб.','Менее 50% вариантов после издержек проходят фолды и holdout.','','research')
    ,('research.degradation.status.no_stable_pass','ru','Нет устойчивых','Нет устойчивых','Нет PASS','Ни один вариант не прошёл полную проверку устойчивости.','','research')
    ,('research.degradation.block.promotion','ru','Продвижение','Продвижение','Стоп','Продвижение этой версии запрещено до строгого PASS.','','research')
    ,('research.degradation.block.quarantine','ru','Карантин','Карантин','Карантин','Три полных деградировавших цикла: прекратить повторный поиск этой версии и создать новую гипотезу.','','research')
    ,('research.degradation.block.none','ru','Разрешено','Разрешено','ОК','Исследовательская версия не требует блокировки.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
    resource_group=EXCLUDED.resource_group;

COMMIT;
