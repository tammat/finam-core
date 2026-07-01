from __future__ import annotations


RU_STATUS = {
    "READY": "Готово",
    "WARNING": "Внимание",
    "HIGH": "Высокий риск",
    "CRITICAL": "Критично",
    "DISABLED": "Отключено",
    "INFO": "Инфо",
    "SAFE": "Безопасно",
}

EN_STATUS = {
    "READY": "Ready",
    "WARNING": "Warning",
    "HIGH": "High Risk",
    "CRITICAL": "Critical",
    "DISABLED": "Disabled",
    "INFO": "Info",
    "SAFE": "Safe",
}


class StatusFormatter:
    @staticmethod
    def normalize(status: str) -> str:
        value = (status or "INFO").upper()
        allowed = {"READY", "WARNING", "HIGH", "CRITICAL", "DISABLED", "INFO", "SAFE"}
        return value if value in allowed else "INFO"

    @staticmethod
    def short(status: str, lang: str = "ru") -> str:
        normalized = StatusFormatter.normalize(status)
        if lang == "en":
            return EN_STATUS.get(normalized, normalized)
        return RU_STATUS.get(normalized, normalized)
