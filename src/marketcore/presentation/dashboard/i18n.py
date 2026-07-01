#!/usr/bin/env python3
from __future__ import annotations

SUPPORTED_LANGUAGES = ("ru", "en")
DEFAULT_LANGUAGE = "ru"

LABELS = {
    "ru": {
        "home": "Главная",
        "market": "Рынок",
        "research": "Исследования",
        "metadata": "Метаданные",
        "risk": "Риски",
        "runtime": "Runtime",
        "versions": "Версии",
        "system": "Система",
        "remediation": "План устранения",
        "ready": "Готово",
        "warning": "Предупреждение",
        "error": "Ошибка",
        "not_built": "Не построено",
        "micro_live_disabled": "Micro Live отключён",
    },
    "en": {
        "home": "Home",
        "market": "Market",
        "research": "Research",
        "metadata": "Metadata",
        "risk": "Risk",
        "runtime": "Runtime",
        "versions": "Versions",
        "system": "System",
        "remediation": "Remediation",
        "ready": "Ready",
        "warning": "Warning",
        "error": "Error",
        "not_built": "Not Built",
        "micro_live_disabled": "Micro Live Disabled",
    },
}

def normalize_language(value: str | None) -> str:
    if value in SUPPORTED_LANGUAGES:
        return value
    return DEFAULT_LANGUAGE

def t(key: str, lang: str | None = None) -> str:
    selected = normalize_language(lang)
    return LABELS[selected].get(key, key)
