# src/scripts/show_trade_journal_from_logs.py

import re
from finam_core.analytics.trade_journal import TradeJournal, TradeRow

PATTERN = re.compile(
    r"PIPE_FILLED .* (?P<symbol>\S+) side=(?P<side>\S+) qty=(?P<qty>[\d\.]+) price=(?P<price>[\d\.]+)"
)

def parse_logs(path: str):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = PATTERN.search(line)
            if not m:
                continue

            rows.append(
                TradeRow(
                    symbol=m.group("symbol"),
                    side=m.group("side"),
                    qty=float(m.group("qty")),
                    price=float(m.group("price")),
                    commission=0.0,
                )
            )
    return rows


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python show_trade_journal_from_logs.py logs.txt")
        return

    rows = parse_logs(sys.argv[1])
    summary = TradeJournal().summarize(rows)

    print("\nЖУРНАЛ СДЕЛОК (из логов)")
    print("=" * 50)
    print(f"Всего сделок          : {summary.trades_count}")
    print(f"Закрытых циклов       : {summary.closed_cycles}")
    print(f"Прибыльных циклов     : {summary.wins}")
    print(f"Убыточных циклов      : {summary.losses}")
    print(f"Winrate               : {summary.winrate:.2%}")
    print(f"Итоговый PnL          : {summary.total_pnl:.4f}")
    print(f"Средний PnL на цикл   : {summary.avg_pnl:.4f}")


if __name__ == "__main__":
    main()
