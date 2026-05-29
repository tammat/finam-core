# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SOURCE_REAL = "paper_pipeline_phase2_runtime"
SOURCE_FORCED = "forced_runtime_governance_observation_v1"


@dataclass(frozen=True)
class ExplainabilityRow:
    source: str
    kind: str
    action: str
    reason: str | None
    session_action: str | None
    strict_reason: str | None
    decay_state: str | None
    total_rows: int
    allowed_rows: int
    blocked_rows: int
    avg_expectancy_points: float | None
    min_expectancy_points: float | None
    max_expectancy_points: float | None


def _git_clean() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return not out.strip()
    except Exception:
        return False


def _fmt_num(value) -> str:
    if value is None:
        return "нет_данных"
    try:
        return f"{float(value):.6f}"
    except Exception:
        return str(value)



def _payload_explainability(row: dict) -> dict:
    value = row.get("explainability")
    return value if isinstance(value, dict) else {}


def _основание_из_payload_или_fallback(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("основание_решения")
    if value:
        return str(value)
    return _основание_решения(row)


def _статус_выборки_из_payload_или_fallback(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("статус_выборки")
    if value:
        return str(value)
    return _статус_выборки(row)


def _решение_из_payload_или_fallback(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("решение")
    if value:
        return str(value)
    return _решение_рус(row)


def _версия_объяснения(row: dict) -> str:
    payload = _payload_explainability(row)
    return str(payload.get("версия_объяснения") or "fallback_runtime_governance_explainability_v1")


def _причина_понятно(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("причина")
    if value:
        return str(value)

    basis = _основание_из_payload_или_fallback(row)
    if basis == "положительное_матожидание":
        return "Исторически это окно показывает положительный результат."
    if basis == "отрицательное_матожидание":
        return "Исторически это окно показывает отрицательный результат."
    if basis == "недостаточно_подтвержденного_преимущества":
        return "Недостаточно статистики для подтверждения преимущества."
    if basis == "сессионная_блокировка":
        return "Сессионный фильтр запрещает вход в этом окне."
    return "Решение принято по правилам Runtime Governance."


def _уровень_уверенности(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("уровень_уверенности")
    if value:
        return str(value)

    total_rows = int(row.get("total_rows") or 0)
    if total_rows >= 100:
        return "высокая"
    if total_rows >= 30:
        return "средняя"
    if total_rows >= 10:
        return "низкая"
    return "очень_низкая"


def _сила_преимущества(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("сила_преимущества")
    if value:
        return str(value)

    expectancy = row.get("avg_expectancy_points")
    if expectancy is None:
        return "не_оценено"

    try:
        exp = float(expectancy)
    except Exception:
        return "не_оценено"

    if exp < 0:
        return "отрицательное"
    if exp >= 0.10:
        return "сильное"
    if exp >= 0.03:
        return "умеренное"
    if exp > 0:
        return "слабое"
    return "нейтральное"


def _доказательства(row: dict) -> str:
    payload = _payload_explainability(row)
    evidence = payload.get("доказательства")
    if isinstance(evidence, dict):
        closed = evidence.get("закрытых_сделок")
        expectancy = evidence.get("матожидание_пункты")
        sample = evidence.get("статус_выборки")
        return f"закрытых_сделок={closed}; матожидание={_fmt_num(expectancy)}; выборка={sample}"

    return (
        f"событий={row.get('total_rows')}; "
        f"матожидание={_fmt_num(row.get('avg_expectancy_points'))}; "
        f"выборка={_статус_выборки_из_payload_или_fallback(row)}"
    )


def _вердикт_из_payload_или_fallback(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("вердикт")
    if value:
        return str(value)
    decision = _решение_из_payload_или_fallback(row)
    if decision == "РАЗРЕШЕНО":
        return "ВХОД РАЗРЕШЕН"
    if decision == "ЗАБЛОКИРОВАНО":
        return "ВХОД ЗАПРЕЩЕН"
    return "ВЕРДИКТ НЕ ОПРЕДЕЛЕН"


def _человеческое_объяснение(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("человеческое_объяснение")
    if value:
        return str(value)
    return _причина_понятно(row)


def _источник_решения(row: dict) -> str:
    payload = _payload_explainability(row)
    value = payload.get("источник_решения")
    if value:
        return str(value)

    reason = str(row.get("reason") or "")
    if reason == "session_side_gate_block":
        return "Сессионная статистика по направлению сделки"
    if reason == "strict_gate_block":
        return "Строгий фильтр Runtime Governance"
    return "Runtime Governance"


def _основание_решения(row: dict) -> str:
    action = str(row.get("action") or "").upper()
    reason = str(row.get("reason") or "")
    strict_reason = str(row.get("strict_reason") or "")
    expectancy = row.get("avg_expectancy_points")
    total_rows = int(row.get("total_rows") or 0)

    if action == "ALLOW":
        if expectancy is not None and float(expectancy) > 0:
            return "положительное_матожидание"
        return "разрешено_по_правилам_governance"

    if reason == "session_side_gate_block":
        if expectancy is not None and float(expectancy) < 0:
            return "отрицательное_матожидание"
        return "сессионная_блокировка"

    if reason == "strict_gate_block":
        if strict_reason == "strict_mode_no_match":
            return "недостаточно_подтвержденного_преимущества"
        return "строгий_фильтр_governance"

    if total_rows < 30:
        return "недостаточно_статистики"

    return "прочее_основание"


def _статус_выборки(row: dict) -> str:
    total_rows = int(row.get("total_rows") or 0)

    if total_rows >= 100:
        return "устойчивая_выборка"
    if total_rows >= 30:
        return "достаточная_выборка"
    if total_rows >= 10:
        return "ранняя_выборка"
    if total_rows > 0:
        return "малая_выборка"
    return "нет_выборки"


def _решение_рус(row: dict) -> str:
    action = str(row.get("action") or "").upper()
    if action == "ALLOW":
        return "РАЗРЕШЕНО"
    if action == "SOFT_BLOCK":
        return "ЗАБЛОКИРОВАНО"
    return action or "НЕИЗВЕСТНО"


SUMMARY_SQL = """
select
    coalesce(raw_json->>'source', 'unknown') as source,
    case
        when raw_json->>'source' = 'paper_pipeline_phase2_runtime' then 'real'
        when raw_json->>'source' = 'forced_runtime_governance_observation_v1' then 'forced'
        else 'other'
    end as kind,
    action,
    reason,
    session_action,
    strict_reason,
    decay_state,
    count(*)::int as total_rows,
    count(*) filter (where allowed is true)::int as allowed_rows,
    count(*) filter (where allowed is false)::int as blocked_rows,
    avg(expectancy_points)::float as avg_expectancy_points,
    min(expectancy_points)::float as min_expectancy_points,
    max(expectancy_points)::float as max_expectancy_points,
    (jsonb_agg(raw_json->'explainability') filter (where raw_json ? 'explainability'))->0 as explainability
from runtime_governance_live_accumulation_v1
where created_at >= now() - (%s::text)::interval
  and coalesce(raw_json->>'source', '') in (
      'paper_pipeline_phase2_runtime',
      'forced_runtime_governance_observation_v1'
  )
group by
    coalesce(raw_json->>'source', 'unknown'),
    kind,
    action,
    reason,
    session_action,
    strict_reason,
    decay_state
order by kind desc, total_rows desc;
"""


SESSION_SQL = """
select
    coalesce(raw_json->>'source', 'unknown') as source,
    case
        when raw_json->>'source' = 'paper_pipeline_phase2_runtime' then 'real'
        when raw_json->>'source' = 'forced_runtime_governance_observation_v1' then 'forced'
        else 'other'
    end as kind,
    hour_msk,
    side,
    action,
    reason,
    count(*)::int as total_rows,
    count(*) filter (where allowed is true)::int as allowed_rows,
    count(*) filter (where allowed is false)::int as blocked_rows,
    avg(expectancy_points)::float as avg_expectancy_points,
    (jsonb_agg(raw_json->'explainability') filter (where raw_json ? 'explainability'))->0 as explainability
from runtime_governance_live_accumulation_v1
where created_at >= now() - (%s::text)::interval
  and coalesce(raw_json->>'source', '') in (
      'paper_pipeline_phase2_runtime',
      'forced_runtime_governance_observation_v1'
  )
group by
    coalesce(raw_json->>'source', 'unknown'),
    kind,
    hour_msk,
    side,
    action,
    reason
order by kind desc, total_rows desc, hour_msk nulls last;
"""


SYMBOL_SQL = """
select
    coalesce(raw_json->>'source', 'unknown') as source,
    case
        when raw_json->>'source' = 'paper_pipeline_phase2_runtime' then 'real'
        when raw_json->>'source' = 'forced_runtime_governance_observation_v1' then 'forced'
        else 'other'
    end as kind,
    symbol,
    side,
    action,
    reason,
    count(*)::int as total_rows,
    count(*) filter (where allowed is true)::int as allowed_rows,
    count(*) filter (where allowed is false)::int as blocked_rows,
    avg(expectancy_points)::float as avg_expectancy_points,
    (jsonb_agg(raw_json->'explainability') filter (where raw_json ? 'explainability'))->0 as explainability
from runtime_governance_live_accumulation_v1
where created_at >= now() - (%s::text)::interval
  and coalesce(raw_json->>'source', '') in (
      'paper_pipeline_phase2_runtime',
      'forced_runtime_governance_observation_v1'
  )
group by
    coalesce(raw_json->>'source', 'unknown'),
    kind,
    symbol,
    side,
    action,
    reason
order by kind desc, total_rows desc, symbol nulls last;
"""


def main() -> int:
    window_hours = int(os.getenv("WINDOW_HOURS", "168"))
    interval_value = f"{window_hours} hours"

    print("RUNTIME_GOVERNANCE_EXPLAINABILITY_V1", flush=True)

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL, (interval_value,))
            summary_rows = cur.fetchall()

            cur.execute(SESSION_SQL, (interval_value,))
            session_rows = cur.fetchall()

            cur.execute(SYMBOL_SQL, (interval_value,))
            symbol_rows = cur.fetchall()

    git_clean = _git_clean()

    print(
        "RUNTIME_GOVERNANCE_EXPLAINABILITY_STATUS",
        f"git_clean={git_clean}",
        f"window_hours={window_hours}",
        f"summary_rows={len(summary_rows)}",
        f"session_rows={len(session_rows)}",
        f"symbol_rows={len(symbol_rows)}",
        flush=True,
    )

    for row in summary_rows:
        row = dict(row)
        print(
            "RUNTIME_GOVERNANCE_EXPLAINABILITY_SUMMARY",
            f"тип={'реальные_события' if row['kind'] == 'real' else 'диагностические_события' if row['kind'] == 'forced' else row['kind']}",
            f"источник={row['source']}",
            f"решение={_решение_из_payload_или_fallback(row)}",
            f"основание={_основание_из_payload_или_fallback(row)}",
            f"статус_выборки={_статус_выборки_из_payload_или_fallback(row)}",
            f"версия_объяснения={_версия_объяснения(row)}",
            f"вердикт={_вердикт_из_payload_или_fallback(row)}",
            f"причина={_причина_понятно(row)}",
            f"уровень_уверенности={_уровень_уверенности(row)}",
            f"сила_преимущества={_сила_преимущества(row)}",
            f"источник_решения={_источник_решения(row)}",
            f"доказательства={_доказательства(row)}",
            f"человеческое_объяснение={_человеческое_объяснение(row)}",
            f"action={row.get('action')}",
            f"reason={row.get('reason')}",
            f"session_action={row.get('session_action')}",
            f"strict_reason={row.get('strict_reason')}",
            f"decay_state={row.get('decay_state')}",
            f"событий={row['total_rows']}",
            f"разрешено={row['allowed_rows']}",
            f"заблокировано={row['blocked_rows']}",
            f"матожидание_среднее={_fmt_num(row.get('avg_expectancy_points'))}",
            f"матожидание_мин={_fmt_num(row.get('min_expectancy_points'))}",
            f"матожидание_макс={_fmt_num(row.get('max_expectancy_points'))}",
            flush=True,
        )

    for row in session_rows:
        row = dict(row)
        print(
            "RUNTIME_GOVERNANCE_EXPLAINABILITY_SESSION",
            f"тип={'реальные_события' if row['kind'] == 'real' else 'диагностические_события' if row['kind'] == 'forced' else row['kind']}",
            f"источник={row['source']}",
            f"час_мск={row.get('hour_msk')}",
            f"сторона={row.get('side')}",
            f"решение={_решение_из_payload_или_fallback(row)}",
            f"основание={_основание_из_payload_или_fallback(row)}",
            f"статус_выборки={_статус_выборки_из_payload_или_fallback(row)}",
            f"версия_объяснения={_версия_объяснения(row)}",
            f"вердикт={_вердикт_из_payload_или_fallback(row)}",
            f"причина={_причина_понятно(row)}",
            f"уровень_уверенности={_уровень_уверенности(row)}",
            f"сила_преимущества={_сила_преимущества(row)}",
            f"источник_решения={_источник_решения(row)}",
            f"доказательства={_доказательства(row)}",
            f"человеческое_объяснение={_человеческое_объяснение(row)}",
            f"событий={row['total_rows']}",
            f"разрешено={row['allowed_rows']}",
            f"заблокировано={row['blocked_rows']}",
            f"матожидание={_fmt_num(row.get('avg_expectancy_points'))}",
            flush=True,
        )

    for row in symbol_rows:
        row = dict(row)
        print(
            "RUNTIME_GOVERNANCE_EXPLAINABILITY_SYMBOL",
            f"тип={'реальные_события' if row['kind'] == 'real' else 'диагностические_события' if row['kind'] == 'forced' else row['kind']}",
            f"источник={row['source']}",
            f"инструмент={row.get('symbol')}",
            f"сторона={row.get('side')}",
            f"решение={_решение_из_payload_или_fallback(row)}",
            f"основание={_основание_из_payload_или_fallback(row)}",
            f"статус_выборки={_статус_выборки_из_payload_или_fallback(row)}",
            f"версия_объяснения={_версия_объяснения(row)}",
            f"вердикт={_вердикт_из_payload_или_fallback(row)}",
            f"причина={_причина_понятно(row)}",
            f"уровень_уверенности={_уровень_уверенности(row)}",
            f"сила_преимущества={_сила_преимущества(row)}",
            f"источник_решения={_источник_решения(row)}",
            f"доказательства={_доказательства(row)}",
            f"человеческое_объяснение={_человеческое_объяснение(row)}",
            f"событий={row['total_rows']}",
            f"разрешено={row['allowed_rows']}",
            f"заблокировано={row['blocked_rows']}",
            f"матожидание={_fmt_num(row.get('avg_expectancy_points'))}",
            flush=True,
        )

    print("RUNTIME_GOVERNANCE_EXPLAINABILITY_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
