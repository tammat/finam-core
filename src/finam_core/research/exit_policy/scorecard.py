from finam_core.research.exit_policy.evaluator import PolicyMetrics


class PolicyScorecard:
    def render_lines(self, metrics: list[PolicyMetrics]) -> list[str]:
        lines = []
        for m in metrics:
            lines.append(
                "EXIT_POLICY_ROW "
                f"policy={m.policy_name} "
                f"trades={m.trades} "
                f"wins={m.wins} "
                f"losses={m.losses} "
                f"winrate={m.winrate:.4f} "
                f"profit_factor={m.profit_factor:.4f} "
                f"expectancy={m.expectancy:.6f} "
                f"gross_pnl={m.gross_pnl:.6f}"
            )
        return lines
