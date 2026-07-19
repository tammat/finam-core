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
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
    resource_group=EXCLUDED.resource_group;

COMMIT;
