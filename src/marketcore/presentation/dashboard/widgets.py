from __future__ import annotations


def status_badge(status: str) -> str:
    normalized = status.upper()
    if normalized == "READY":
        return "READY"
    if normalized in {"WARNING", "HIGH", "HIGH_RISK"}:
        return "WARNING"
    if normalized in {"ERROR", "CRITICAL"}:
        return "ERROR"
    return "DISABLED"


def metric_card(title: str, value: str, status: str = "READY") -> dict[str, str]:
    return {
        "title": title,
        "value": value,
        "status": status_badge(status),
    }
