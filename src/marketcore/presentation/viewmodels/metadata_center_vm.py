from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetadataMetricVM:
    title: str
    value: str
    status: str
    action_label: str = "Подробнее"
    action_href: str = "#"


@dataclass(frozen=True)
class MetadataObjectVM:
    name: str
    layer: str
    rows_count: str
    quality: str
    status: str


@dataclass(frozen=True)
class MetadataSourceVM:
    source: str
    objects: str
    coverage: str
    status: str


@dataclass(frozen=True)
class MetadataCenterVM:
    title: str = "Метаданные"
    subtitle: str = "Metadata Center"

    overview: list[MetadataMetricVM] = field(default_factory=list)
    objects: list[MetadataObjectVM] = field(default_factory=list)
    sources: list[MetadataSourceVM] = field(default_factory=list)
    actions: list[MetadataMetricVM] = field(default_factory=list)


def build_default_metadata_center_vm() -> MetadataCenterVM:
    return MetadataCenterVM(
        overview=[
            MetadataMetricVM("Объекты", "373", "READY", "Открыть", "/metadata"),
            MetadataMetricVM("Источн.", "12", "READY", "Детали", "/metadata"),
            MetadataMetricVM("Покрытие", "100%", "READY", "Детали", "/metadata"),
            MetadataMetricVM("Качество", "100%", "READY", "Детали", "/metadata"),
        ],
        objects=[
            MetadataObjectVM("Рыночные бары", "Рынок", "876 тыс.", "100%", "READY"),
            MetadataObjectVM("Рыночные тики", "Рынок", "71,1 млн.", "100%", "READY"),
            MetadataObjectVM("Исследования", "Research", "1", "Готово", "READY"),
        ],
        sources=[
            MetadataSourceVM("PostgreSQL", "373", "100%", "READY"),
            MetadataSourceVM("Finam", "59", "100%", "READY"),
            MetadataSourceVM("Research", "1", "Готово", "READY"),
        ],
        actions=[
            MetadataMetricVM("Диагн.", "Открыть", "INFO", "Открыть", "/system"),
            MetadataMetricVM("Рынок", "Открыть", "READY", "Открыть", "/market"),
            MetadataMetricVM("Исслед.", "Открыть", "READY", "Открыть", "/research"),
        ],
    )
