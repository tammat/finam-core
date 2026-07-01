from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.components.badges import Badge
from marketcore.presentation.design_system.registry import DesignComponent, design_registry
from marketcore.presentation.formatters.status_formatter import StatusFormatter


def _status_label(status: str) -> str:
    return StatusFormatter.short(status, "ru")


def Card(title: str, body: str) -> str:
    return (
        '<section class="fc-card">'
        f'<h3>{escape(str(title))}</h3>'
        f'<div>{body}</div>'
        '</section>'
    )


def _display_value(value: str | int | float) -> str:
    text = str(value)
    normalized = text.upper()
    if normalized in {"READY", "WARNING", "HIGH", "CRITICAL", "DISABLED", "INFO", "SAFE"}:
        return StatusFormatter.short(normalized, "ru")
    return text


def MetricCard(title: str, value: str | int | float, status: str = "READY") -> str:
    return Card(
        title,
        f'<div class="fc-metric">{escape(_display_value(value))}</div>{Badge(_status_label(status), status)}',
    )


def HealthCard(title: str, status: str = "READY") -> str:
    return Card(title, Badge(_status_label(status), status))


def StatusCard(title: str, status: str) -> str:
    return Card(title, Badge(_status_label(status), status))


def VersionCard(title: str, version: str) -> str:
    return Card(title, f'<code>{escape(str(version))}</code>')


def KeyValueCard(title: str, items: dict[str, str | int | float]) -> str:
    rows = "".join(
        f'<div class="fc-kv-row"><span>{escape(str(k))}</span><strong>{escape(str(v))}</strong></div>'
        for k, v in items.items()
    )
    return Card(title, rows)


design_registry.register(DesignComponent("HealthCard", "cards"))
design_registry.register(DesignComponent("MetricCard", "cards"))
design_registry.register(DesignComponent("StatusCard", "cards"))
design_registry.register(DesignComponent("VersionCard", "cards"))
design_registry.register(DesignComponent("KeyValueCard", "cards"))
