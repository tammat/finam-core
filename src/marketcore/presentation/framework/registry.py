from __future__ import annotations

from enum import StrEnum


class WidgetType(StrEnum):
    BASE = "BASE"
    KPI = "KPI"
    BADGE = "BADGE"
    PROGRESS = "PROGRESS"
    STATUS = "STATUS"
    CHART = "CHART"
    TABLE = "TABLE"
    TIMELINE = "TIMELINE"


class CardType(StrEnum):
    BASE = "BASE"
    KPI = "KPI"
    ACTION = "ACTION"
    ALERT = "ALERT"
    DECISION = "DECISION"
    INSTRUMENT = "INSTRUMENT"
    TIMELINE = "TIMELINE"
    CHART = "CHART"


class SectionType(StrEnum):
    SUMMARY = "SUMMARY"
    PORTFOLIO = "PORTFOLIO"
    PROBE = "PROBE"
    RESEARCH = "RESEARCH"
    OBSERVATION = "OBSERVATION"
    RUNTIME = "RUNTIME"
    ACTIONS = "ACTIONS"
    ALERTS = "ALERTS"


class LayoutType(StrEnum):
    PHONE = "PHONE"
    TABLET = "TABLET"
    DESKTOP = "DESKTOP"


class UiStatusCode(StrEnum):
    DEFAULT = "DEFAULT"
    OK = "OK"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"
    LOCKED = "LOCKED"
    ERROR = "ERROR"
    ARCHIVED = "ARCHIVED"
    FALLBACK = "FALLBACK"


class ActionCode(StrEnum):
    OPEN = "OPEN"
    DETAILS = "DETAILS"
    BACK = "BACK"
    HOME = "HOME"
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
