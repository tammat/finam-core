from __future__ import annotations

from marketcore.presentation.workspace_v2.mission_control_v1 import render_mission_control_v1


def render_workspace_v2_home_v1() -> str:
    html = render_mission_control_v1()
    return html.replace("Центр управления", "Главная").replace("Mission Control", "Главная")
