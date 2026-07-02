from __future__ import annotations


class StatusService:
    LABELS_RU = {
        "OK": "ОК",
        "READY": "Готово",
        "RUNNING": "Работает",
        "BLOCKED": "Заблокировано",
        "ERROR": "Ошибка",
        "WARNING": "Предупреждение",
        "VALIDATED": "Подтверждено",
        "REJECTED": "Отклонено",
        "UNKNOWN": "Неизвестно",
        "OFF": "Выключено",
        "ON": "Включено",
        "SAFE": "Безопасно",
        "STALE": "Устарело",
        "FRESH": "Актуально",
    }

    def label(self, status: str | None, locale: str = "ru") -> str:
        key = (status or "UNKNOWN").upper()
        if locale == "ru":
            return self.LABELS_RU.get(key, key)
        return key

    def severity(self, status: str | None) -> str:
        key = (status or "UNKNOWN").upper()
        if key in {"OK", "READY", "RUNNING", "VALIDATED", "ON", "SAFE", "FRESH"}:
            return "ok"
        if key in {"WARNING", "BLOCKED", "STALE"}:
            return "warn"
        if key in {"ERROR", "REJECTED"}:
            return "error"
        if key in {"OFF", "UNKNOWN"}:
            return "off"
        return "unknown"
