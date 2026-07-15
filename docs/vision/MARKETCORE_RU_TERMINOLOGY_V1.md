# MarketCore Russian Operator Terminology V1

## Purpose

This glossary is mandatory for every operator-facing message in RenderTree V2.
Internal domain codes, database identifiers, exchange symbols and audit codes remain stable and language-independent.
They must not be rendered as operator labels.

## Required Terms

| Internal term | Russian operator text |
|---|---|
| Edge | статистическое преимущество |
| OOS | вневыборочная проверка |
| PnL | финансовый результат |
| ROI | рентабельность капитала |
| Paper | модельный режим; модельные сделки |
| Shadow | теневой режим; теневые сделки |
| Forward | проверка на последующих данных |
| Live | реальные торги; боевой контур |
| bid/ask | лучшие цены покупки и продажи |
| order book | биржевой стакан |
| drawdown | просадка |
| profit factor | коэффициент прибыли |
| expectancy | ожидаемый результат на сделку |
| trailing stop | динамический защитный стоп-приказ |
| ATR | средний истинный диапазон |
| cohort | группа наблюдений |
| eligible | соответствует условиям |
| runtime | исполняющий контур |
| pipeline | последовательность обработки |
| worker | обработчик очереди |
| rollback | отмена операции |
| freshness | актуальность данных |
| lineage | происхождение данных |
| guard | контрольное ограничение |

## Rules

1. Do not construct Russian labels by translating individual fragments of a resource key.
2. Prefer the full Russian term; do not invent Russian abbreviations.
3. A stable exchange symbol, instrument ticker or registered product name is domain data, not a translatable label.
4. An English internal code may be shown only in a diagnostic or audit field explicitly intended for engineers.
5. Parameter labels must describe financial meaning and units, not database column names.
6. Every new operator-facing term requires a glossary review before its catalog entry is accepted.
