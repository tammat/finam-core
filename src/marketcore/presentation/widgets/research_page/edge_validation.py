from __future__ import annotations

import html


class ResearchEdgeValidationWidget:
    def render(self, vm) -> str:
        rows = []

        for item in vm.edge_validation:
            cost_status = str(
                item.cost_status
            )

            if (
                cost_status
                == "REJECT_AFTER_BASE_COSTS"
            ):
                cost_label = (
                    "ОТКЛОНЕНО ПО БАЗОВЫМ COSTS"
                )
            elif (
                cost_status
                == "FUTURES_COST_SEMANTICS_PENDING"
            ):
                cost_label = (
                    "ОЖИДАЕТ FUTURES COSTS"
                )
            elif (
                cost_status
                == "COST_VALIDATION_PENDING"
            ):
                cost_label = (
                    "ОЖИДАЕТ COST VALIDATION"
                )
            else:
                cost_label = cost_status

            values = (
                item.symbol,
                item.robustness,
                item.positive_variants,
                item.stable_variants,
                cost_label,
                item.net_pnl,
                item.net_expectancy,
                item.net_profit_factor,
                item.economic_edge,
                item.micro_live,
            )

            cells = "".join(
                f"<td>{html.escape(str(value))}</td>"
                for value in values
            )

            rows.append(
                f"<tr>{cells}</tr>"
            )

        if not rows:
            rows.append(
                '<tr><td colspan="10">'
                'Нет данных Edge Validation.'
                '</td></tr>'
            )

        return (
            '<section class="fc-card">'
            '<h2>Валидация edge</h2>'
            '<p>'
            'Robustness → costs → экономический edge → micro live.'
            '</p>'
            '<div style="overflow-x:auto;">'
            '<table>'
            '<thead><tr>'
            '<th>Инструмент</th>'
            '<th>Robustness</th>'
            '<th>Положительные варианты</th>'
            '<th>Стабильные варианты</th>'
            '<th>Costs</th>'
            '<th>Net PnL</th>'
            '<th>Net expectancy</th>'
            '<th>Net PF</th>'
            '<th>Economic edge</th>'
            '<th>Micro live</th>'
            '</tr></thead>'
            '<tbody>'
            + "".join(rows)
            + '</tbody>'
            '</table>'
            '</div>'
            '</section>'
        )
