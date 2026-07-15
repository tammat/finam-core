from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import (
    DomainProducerCodeV2,
)


class ContainerCodeV2(str, Enum):
    HOME = "HOME"
    CAPITAL = "CAPITAL"
    EDGE = "EDGE"
    RESEARCH = "RESEARCH"
    INTRADAY = "INTRADAY"
    PORTFOLIO = "PORTFOLIO"
    RISK = "RISK"
    PROGRAM = "PROGRAM"
    SETTINGS = "SETTINGS"


class ContainerViewStateV2(str, Enum):
    LOADING = "LOADING"
    READY = "READY"
    EMPTY = "EMPTY"
    FAILURE = "FAILURE"


@dataclass(frozen=True, slots=True)
class ContainerDefinitionV2:
    container_code: ContainerCodeV2
    container_id: str
    label_message_key: str
    owner_code: str
    display_order: int
    producer_code: DomainProducerCodeV2 | None
    supported_states: tuple[ContainerViewStateV2, ...]

    @property
    def target_ready(self) -> bool:
        return self.producer_code is not None


_ALL_STATES = tuple(ContainerViewStateV2)


def _definition(
    code: ContainerCodeV2,
    owner_code: str,
    order: int,
    producer_code: DomainProducerCodeV2 | None = None,
) -> ContainerDefinitionV2:
    slug = code.value.lower()
    return ContainerDefinitionV2(
        container_code=code,
        container_id=f"container.{slug}",
        label_message_key=f"navigation.container.{slug}",
        owner_code=owner_code,
        display_order=order,
        producer_code=producer_code,
        supported_states=_ALL_STATES,
    )


_DEFINITIONS: Mapping[ContainerCodeV2, ContainerDefinitionV2] = MappingProxyType(
    {
        ContainerCodeV2.HOME: _definition(ContainerCodeV2.HOME, "OPERATOR_HOME", 10, DomainProducerCodeV2.HOME),
        ContainerCodeV2.CAPITAL: _definition(ContainerCodeV2.CAPITAL, "CAPITAL", 20, DomainProducerCodeV2.CAPITAL),
        ContainerCodeV2.EDGE: _definition(ContainerCodeV2.EDGE, "EDGE_CONTROL", 30, DomainProducerCodeV2.CONTROL_CENTER),
        ContainerCodeV2.RESEARCH: _definition(ContainerCodeV2.RESEARCH, "RESEARCH", 40),
        ContainerCodeV2.INTRADAY: _definition(ContainerCodeV2.INTRADAY, "INTRADAY", 50),
        ContainerCodeV2.PORTFOLIO: _definition(ContainerCodeV2.PORTFOLIO, "PORTFOLIO", 60, DomainProducerCodeV2.PORTFOLIO),
        ContainerCodeV2.RISK: _definition(ContainerCodeV2.RISK, "RISK", 70, DomainProducerCodeV2.RISK),
        ContainerCodeV2.PROGRAM: _definition(ContainerCodeV2.PROGRAM, "PROGRAM", 80),
        ContainerCodeV2.SETTINGS: _definition(ContainerCodeV2.SETTINGS, "SETTINGS", 90, DomainProducerCodeV2.SETTINGS),
    }
)

_BY_ID: Mapping[str, ContainerDefinitionV2] = MappingProxyType(
    {definition.container_id: definition for definition in _DEFINITIONS.values()}
)


def container_definitions_v2() -> tuple[ContainerDefinitionV2, ...]:
    return tuple(sorted(_DEFINITIONS.values(), key=lambda item: item.display_order))


def resolve_container_v2(container_id: str) -> ContainerDefinitionV2:
    try:
        return _BY_ID[container_id]
    except KeyError as exc:
        raise ValueError(f"CONTAINER_V2_UNKNOWN:{container_id}") from exc


def ready_container_definitions_v2() -> tuple[ContainerDefinitionV2, ...]:
    return tuple(item for item in container_definitions_v2() if item.target_ready)
