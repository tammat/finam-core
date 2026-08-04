from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from marketcore.presentation.api_client import get_json


DECISION_FUNNEL_ENDPOINT = (
    "/api/kg/v1/decision-funnel"
    "?hours=24"
    "&recent_limit=50"
    "&reason_limit=20"
    "&dimension_limit=100"
)

STAGE_TITLES: dict[str, str] = {
    "MARKET_DATA": "Рыночные данные",
    "STRATEGY": "Стратегия",
    "REGIME": "Рыночный режим",
    "EDGE": "Подтверждение edge",
    "RISK": "Риск-контроль",
    "PORTFOLIO": "Портфель",
    "RUNTIME": "Runtime governance",
    "EXECUTION": "Исполнение",
    "BROKER": "Брокер",
    "FILL": "Исполнение заявки",
}

OUTCOME_TITLES: dict[str, str] = {
    "PASS": "Пройдено",
    "REJECT": "Отклонено",
    "ERROR": "Ошибка",
    "SKIP": "Пропущено",
}

REASON_TITLES: dict[str, str] = {
    "PASSED": "Проверка пройдена",
    "NO_SIGNAL": "Стратегия не сформировала сигнал",
    "STRATEGY_DISABLED": "Стратегия отключена",
    "REGIME_NOT_ALLOWED": "Рыночный режим не разрешён",
    "REGIME_UNKNOWN": "Рыночный режим не определён",
    "EDGE_NOT_CONFIRMED": "Edge не подтверждён",
    "EDGE_SCORE_TOO_LOW": "Недостаточный edge score",
    "CONFIDENCE_TOO_LOW": "Недостаточная уверенность",
    "SAMPLE_TOO_SMALL": "Недостаточный объём выборки",
    "MAX_RISK_PER_TRADE": "Превышен риск на сделку",
    "DAILY_LOSS_LIMIT": "Достигнут дневной лимит потерь",
    "EXPOSURE_LIMIT": "Превышен лимит экспозиции",
    "CORRELATION_FILTER": "Отклонено корреляционным фильтром",
    "KILL_SWITCH": "Активирован kill switch",
    "POSITION_ALREADY_OPEN": "Позиция уже открыта",
    "PORTFOLIO_LIMIT": "Достигнут портфельный лимит",
    "RUNTIME_NOT_ALLOWED": "Runtime не разрешён",
    "SHADOW_ONLY": "Разрешён только shadow-режим",
    "PAPER_ONLY": "Разрешён только paper-режим",
    "MICRO_LIVE_NOT_ALLOWED": "Micro Live не разрешён",
    "MARKET_CLOSED": "Рынок закрыт",
    "EXECUTION_DISABLED": "Исполнение отключено",
    "ORDER_REJECTED": "Заявка отклонена",
    "BROKER_UNAVAILABLE": "Брокер недоступен",
    "BROKER_REJECTED": "Брокер отклонил заявку",
    "FILL_TIMEOUT": "Истекло время ожидания исполнения",
}


@dataclass(frozen=True, slots=True)
class DecisionFunnelSectionV1:
    """Read-only payload секции Control V3."""

    section_id: str
    title: str
    status: str
    summary_rows: tuple[dict[str, Any], ...]
    stage_rows: tuple[dict[str, Any], ...]
    rejection_rows: tuple[dict[str, Any], ...]
    dimension_rows: tuple[dict[str, Any], ...]
    recent_rows: tuple[dict[str, Any], ...]
    metadata: Mapping[str, Any]


def _integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _percentage(value: Any) -> str:
    if value in (None, ""):
        return "—"

    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "—"


def _rows(value: Any) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, list):
        return ()

    return tuple(
        row
        for row in value
        if isinstance(row, Mapping)
    )


def _unavailable_section(
    metadata: Mapping[str, Any] | None = None,
) -> DecisionFunnelSectionV1:
    return DecisionFunnelSectionV1(
        section_id="decision_funnel",
        title="Воронка торговых решений",
        status="UNAVAILABLE",
        summary_rows=(
            {
                "status": "UNAVAILABLE",
                "signal_count": 0,
                "event_count": 0,
                "reject_events": 0,
                "error_events": 0,
                "rejection_rate": "—",
                "message": (
                    "Read-only endpoint Decision Funnel недоступен"
                ),
            },
        ),
        stage_rows=(),
        rejection_rows=(),
        dimension_rows=(),
        recent_rows=(),
        metadata={
            "read_only": 1,
            "ui_direct_sql": 0,
            "runtime_instrumentation": 0,
            "write_actions_allowed": 0,
            "error": dict(metadata or {}),
        },
    )


def load_decision_funnel_section_v1(
    *,
    endpoint: str = DECISION_FUNNEL_ENDPOINT,
) -> DecisionFunnelSectionV1:
    """
    Получить Decision Funnel только через KG API.

    SQL fallback запрещён. Недоступность API отображается как
    UNAVAILABLE и не влияет на Control V3 или торговый runtime.
    """

    payload = get_json(endpoint, timeout=3.0)

    if not isinstance(payload, Mapping):
        return _unavailable_section()

    data = payload.get("data")

    if not isinstance(data, Mapping):
        metadata = payload.get("metadata")

        return _unavailable_section(
            metadata
            if isinstance(metadata, Mapping)
            else None
        )

    summary = data.get("summary")
    summary = (
        summary
        if isinstance(summary, Mapping)
        else {}
    )

    status = _text(data.get("status") or "EMPTY")

    summary_rows = (
        {
            "status": status,
            "signal_count": _integer(
                summary.get("signal_count")
            ),
            "event_count": _integer(
                summary.get("event_count")
            ),
            "pass_events": _integer(
                summary.get("pass_events")
            ),
            "reject_events": _integer(
                summary.get("reject_events")
            ),
            "error_events": _integer(
                summary.get("error_events")
            ),
            "skip_events": _integer(
                summary.get("skip_events")
            ),
            "symbol_count": _integer(
                summary.get("symbol_count")
            ),
            "strategy_count": _integer(
                summary.get("strategy_count")
            ),
            "rejection_rate": _percentage(
                summary.get("rejection_rate")
            ),
            "first_event_at": summary.get(
                "first_event_at"
            ),
            "last_event_at": summary.get(
                "last_event_at"
            ),
        },
    )

    stage_rows = tuple(
        {
            "position": _integer(row.get("position")),
            "stage": _text(row.get("stage")),
            "stage_title": STAGE_TITLES.get(
                _text(row.get("stage")),
                _text(row.get("stage")),
            ),
            "signal_count": _integer(
                row.get("signal_count")
            ),
            "passed_signals": _integer(
                row.get("passed_signals")
            ),
            "rejected_signals": _integer(
                row.get("rejected_signals")
            ),
            "error_signals": _integer(
                row.get("error_signals")
            ),
            "skipped_signals": _integer(
                row.get("skipped_signals")
            ),
            "pass_rate": _percentage(
                row.get("pass_rate")
            ),
            "rejection_rate": _percentage(
                row.get("rejection_rate")
            ),
            "previous_observed_stage": row.get(
                "previous_observed_stage"
            ),
            "conversion_from_previous_stage": (
                _percentage(
                    row.get(
                        "conversion_from_previous_stage"
                    )
                )
            ),
        }
        for row in _rows(data.get("stage_funnel"))
    )

    rejection_rows = tuple(
        {
            "stage": _text(row.get("stage")),
            "stage_title": STAGE_TITLES.get(
                _text(row.get("stage")),
                _text(row.get("stage")),
            ),
            "reason_code": _text(
                row.get("reason_code")
            ),
            "reason_title": REASON_TITLES.get(
                _text(row.get("reason_code")),
                _text(row.get("reason_code")),
            ),
            "signal_count": _integer(
                row.get("signal_count")
            ),
            "event_count": _integer(
                row.get("event_count")
            ),
            "last_seen_at": row.get("last_seen_at"),
        }
        for row in _rows(
            data.get("top_rejection_reasons")
        )
    )

    dimension_rows = tuple(
        {
            "symbol": _text(row.get("symbol")),
            "strategy": _text(row.get("strategy")),
            "timeframe": _text(row.get("timeframe")),
            "signal_count": _integer(
                row.get("signal_count")
            ),
            "event_count": _integer(
                row.get("event_count")
            ),
            "rejected_signals": _integer(
                row.get("rejected_signals")
            ),
            "filled_signals": _integer(
                row.get("filled_signals")
            ),
            "last_event_at": row.get("last_event_at"),
        }
        for row in _rows(data.get("dimensions"))
    )

    recent_rows = tuple(
        {
            "occurred_at": row.get("occurred_at"),
            "signal_id": _text(row.get("signal_id")),
            "symbol": _text(row.get("symbol")),
            "strategy": _text(row.get("strategy")),
            "timeframe": _text(row.get("timeframe")),
            "direction": row.get("direction"),
            "stage": _text(row.get("stage")),
            "stage_title": STAGE_TITLES.get(
                _text(row.get("stage")),
                _text(row.get("stage")),
            ),
            "outcome": _text(row.get("outcome")),
            "outcome_title": OUTCOME_TITLES.get(
                _text(row.get("outcome")),
                _text(row.get("outcome")),
            ),
            "reason_code": _text(
                row.get("reason_code")
            ),
            "reason_title": REASON_TITLES.get(
                _text(row.get("reason_code")),
                _text(row.get("reason_code")),
            ),
            "attempt_no": _integer(
                row.get("attempt_no")
            ),
            "source": _text(row.get("source")),
        }
        for row in _rows(data.get("recent_events"))
    )

    metadata = data.get("metadata")
    metadata = (
        dict(metadata)
        if isinstance(metadata, Mapping)
        else {}
    )

    metadata.update(
        {
            "endpoint": endpoint,
            "read_only": 1,
            "ui_direct_sql": 0,
            "runtime_instrumentation": 0,
            "write_actions_allowed": 0,
        }
    )

    return DecisionFunnelSectionV1(
        section_id="decision_funnel",
        title="Воронка торговых решений",
        status=status,
        summary_rows=summary_rows,
        stage_rows=stage_rows,
        rejection_rows=rejection_rows,
        dimension_rows=dimension_rows,
        recent_rows=recent_rows,
        metadata=metadata,
    )


def decision_funnel_render_sections_v1(
    *,
    endpoint: str = DECISION_FUNNEL_ENDPOINT,
) -> tuple[tuple[str, tuple[dict[str, Any], ...]], ...]:
    """
    Секции нейтрального Render Tree.

    Формат не содержит HTML и не зависит от конкретного renderer.
    """

    section = load_decision_funnel_section_v1(
        endpoint=endpoint
    )

    return (
        (
            "decision_funnel_summary",
            section.summary_rows,
        ),
        (
            "decision_funnel_stages",
            section.stage_rows,
        ),
        (
            "decision_funnel_rejections",
            section.rejection_rows,
        ),
        (
            "decision_funnel_dimensions",
            section.dimension_rows,
        ),
        (
            "decision_funnel_recent",
            section.recent_rows,
        ),
    )
