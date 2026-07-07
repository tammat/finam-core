from __future__ import annotations

from html import escape


def render_action_panel(actions: list[dict]) -> str:
    html = ['<div class="action-grid">']

    for action in actions:
        html.append(
            f'''
            <form method="post"
                  action="/edge-discovery/command">
                <input type="hidden"
                       name="command_code"
                       value="{escape(action["command_code"])}">
                <button class="action-button">
                    {escape(action["caption"])}
                </button>
            </form>
            '''
        )

    html.append("</div>")

    return "".join(html)
