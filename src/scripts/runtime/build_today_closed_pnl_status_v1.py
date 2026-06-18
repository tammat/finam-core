#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TODAY_CLOSED_PNL_STATUS_V1 — read-only восстановление дневного closed PnL.
# Скрипт не меняет БД, runtime, execution и real trading.
# PnL считается приблизительно по FIFO из таблицы trades:
# BUY увеличивает long inventory, SELL закрывает long inventory.
# Для SELL->BUY short recovery пока не считаем как полноценный short accounting,
# но open tail показываем отдельно.


TRADES_SQL = """
select
    id,
    created_at,
    symbol,
    strategy,
    timeframe,
    side,
    qty,
    price,
    commission,
    trade_source,
    origin,
    payload
from trades
where created_at::date = current_date
  and coalesce(is_invalid, false) = false
order by created_at asc, id asc;
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


@dataclass
class TradeRow:
    id: int
    created_at: str
    symbol: str
    strategy: str
    timeframe: str
    side: str
    qty: float
    price: float
    commission: float
    trade_source: str
    origin: str


@dataclass
class ClosedCycle:
    symbol: str
    strategy: str
    timeframe: str
    open_time: str
    close_time: str
    open_side: str
    close_side: str
    qty: float
    open_price: float
    close_price: float
    gross_pnl: float
    commission: float
    net_pnl: float


@dataclass
class SymbolSummary:
    symbol: str
    strategy: str
    timeframe: str
    trades: int
    buy_trades: int
    sell_trades: int
    closed_cycles: int
    closed_qty: float
    open_qty: float
    gross_pnl: float
    commission: float
    net_pnl: float
    first_trade: str
    last_trade: str


def fetch_trades() -> list[TradeRow]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is required")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRADES_SQL)
            rows = cur.fetchall()

    result: list[TradeRow] = []
    for row in rows:
        result.append(
            TradeRow(
                id=int(row.get("id") or 0),
                created_at=str(row.get("created_at")),
                symbol=norm(row.get("symbol")) or "UNKNOWN",
                strategy=norm(row.get("strategy")) or "UNKNOWN",
                timeframe=norm(row.get("timeframe")) or "UNKNOWN",
                side=norm(row.get("side")).upper() or "UNKNOWN",
                qty=fnum(row.get("qty")),
                price=fnum(row.get("price")),
                commission=fnum(row.get("commission")),
                trade_source=norm(row.get("trade_source")),
                origin=norm(row.get("origin")),
            )
        )

    return result


def reconstruct_fifo(trades: list[TradeRow]) -> tuple[list[ClosedCycle], dict[tuple[str, str, str], float]]:
    # Русский комментарий:
    # long_inventory хранит BUY-лоты. SELL закрывает BUY по FIFO.
    # short/open SELL без BUY пока учитывается как отрицательный open_tail.
    long_inventory: dict[tuple[str, str, str], deque[TradeRow]] = defaultdict(deque)
    open_tail: dict[tuple[str, str, str], float] = defaultdict(float)
    closed: list[ClosedCycle] = []

    for trade in trades:
        key = (trade.symbol, trade.strategy, trade.timeframe)
        side = trade.side
        qty_left = trade.qty

        if qty_left <= 0:
            continue

        if side in ("BUY", "LONG"):
            long_inventory[key].append(trade)
            open_tail[key] += qty_left
            continue

        if side in ("SELL", "SHORT"):
            # Русский комментарий: закрываем long inventory.
            while qty_left > 1e-12 and long_inventory[key]:
                open_trade = long_inventory[key][0]
                match_qty = min(qty_left, open_trade.qty)

                gross = (trade.price - open_trade.price) * match_qty
                commission = (open_trade.commission + trade.commission) * (match_qty / max(trade.qty, 1e-12))
                net = gross - commission

                closed.append(
                    ClosedCycle(
                        symbol=trade.symbol,
                        strategy=trade.strategy,
                        timeframe=trade.timeframe,
                        open_time=open_trade.created_at,
                        close_time=trade.created_at,
                        open_side="BUY",
                        close_side="SELL",
                        qty=match_qty,
                        open_price=open_trade.price,
                        close_price=trade.price,
                        gross_pnl=gross,
                        commission=commission,
                        net_pnl=net,
                    )
                )

                open_trade.qty -= match_qty
                qty_left -= match_qty
                open_tail[key] -= match_qty

                if open_trade.qty <= 1e-12:
                    long_inventory[key].popleft()

            # Русский комментарий: если SELL остался без BUY, это short/open tail.
            if qty_left > 1e-12:
                open_tail[key] -= qty_left

    return closed, dict(open_tail)


def build_status() -> dict[str, Any]:
    trades = fetch_trades()
    closed, open_tail = reconstruct_fifo([TradeRow(**asdict(t)) for t in trades])

    groups: dict[tuple[str, str, str], list[TradeRow]] = defaultdict(list)
    for trade in trades:
        groups[(trade.symbol, trade.strategy, trade.timeframe)].append(trade)

    closed_by_key: dict[tuple[str, str, str], list[ClosedCycle]] = defaultdict(list)
    for cycle in closed:
        closed_by_key[(cycle.symbol, cycle.strategy, cycle.timeframe)].append(cycle)

    summaries: list[SymbolSummary] = []
    for key, group in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        symbol, strategy, timeframe = key
        cycles = closed_by_key.get(key, [])
        gross = sum(c.gross_pnl for c in cycles)
        commission = sum(c.commission for c in cycles)
        net = sum(c.net_pnl for c in cycles)

        summaries.append(
            SymbolSummary(
                symbol=symbol,
                strategy=strategy,
                timeframe=timeframe,
                trades=len(group),
                buy_trades=sum(1 for t in group if t.side in ("BUY", "LONG")),
                sell_trades=sum(1 for t in group if t.side in ("SELL", "SHORT")),
                closed_cycles=len(cycles),
                closed_qty=sum(c.qty for c in cycles),
                open_qty=open_tail.get(key, 0.0),
                gross_pnl=gross,
                commission=commission,
                net_pnl=net,
                first_trade=group[0].created_at,
                last_trade=group[-1].created_at,
            )
        )

    total_net = sum(s.net_pnl for s in summaries)
    total_gross = sum(s.gross_pnl for s in summaries)
    total_commission = sum(s.commission for s in summaries)
    total_closed_cycles = sum(s.closed_cycles for s in summaries)

    context_clean = all(t.strategy and t.timeframe and t.symbol for t in trades)

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "mode": "read_only",
        "runtime_allow": 0,
        "execution_enabled": 0,
        "real_trading_enabled": 0,
        "db_update": 0,
        "trades_today": len(trades),
        "symbols": len(summaries),
        "closed_cycles": total_closed_cycles,
        "gross_pnl": total_gross,
        "commission": total_commission,
        "net_pnl": total_net,
        "context_clean": 1 if context_clean else 0,
        "summaries": [asdict(s) for s in summaries],
        "recent_trades": [asdict(t) for t in sorted(trades, key=lambda x: x.created_at, reverse=True)[:20]],
        "recent_closed_cycles": [asdict(c) for c in sorted(closed, key=lambda x: x.close_time, reverse=True)[:20]],
        "verdict": "TODAY_CLOSED_PNL_STATUS_OK" if context_clean else "TODAY_CLOSED_PNL_CONTEXT_HAS_GAPS",
    }


def print_cli(status: dict[str, Any]) -> None:
    print("=== TODAY CLOSED PNL STATUS V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    print("TODAY_CLOSED_PNL_SUMMARY")
    print(f"generated_at={status['generated_at']}")
    print(f"trades_today={status['trades_today']}")
    print(f"symbols={status['symbols']}")
    print(f"closed_cycles={status['closed_cycles']}")
    print(f"gross_pnl={status['gross_pnl']:.6f}")
    print(f"commission={status['commission']:.6f}")
    print(f"net_pnl={status['net_pnl']:.6f}")
    print(f"context_clean={status['context_clean']}")

    print()
    print("TODAY_CLOSED_PNL_BY_SYMBOL")
    for row in status["summaries"]:
        print(
            "TODAY_CLOSED_PNL_SYMBOL_ROW "
            f"symbol={row['symbol']} "
            f"strategy={row['strategy']} "
            f"timeframe={row['timeframe']} "
            f"trades={row['trades']} "
            f"buy_trades={row['buy_trades']} "
            f"sell_trades={row['sell_trades']} "
            f"closed_cycles={row['closed_cycles']} "
            f"closed_qty={row['closed_qty']:.6f} "
            f"open_qty={row['open_qty']:.6f} "
            f"gross_pnl={row['gross_pnl']:.6f} "
            f"commission={row['commission']:.6f} "
            f"net_pnl={row['net_pnl']:.6f} "
            f"first_trade={row['first_trade']} "
            f"last_trade={row['last_trade']}"
        )

    print()
    print("TODAY_CLOSED_PNL_RECENT_CYCLES")
    for row in status["recent_closed_cycles"]:
        print(
            "TODAY_CLOSED_PNL_CYCLE_ROW "
            f"symbol={row['symbol']} "
            f"strategy={row['strategy']} "
            f"timeframe={row['timeframe']} "
            f"qty={row['qty']:.6f} "
            f"open_price={row['open_price']:.6f} "
            f"close_price={row['close_price']:.6f} "
            f"gross_pnl={row['gross_pnl']:.6f} "
            f"net_pnl={row['net_pnl']:.6f} "
            f"open_time={row['open_time']} "
            f"close_time={row['close_time']}"
        )

    print()
    print("TODAY_CLOSED_PNL_STATUS_SUMMARY")
    print(f"verdict={status['verdict']}")
    print("db_update=0")
    print(f"VERDICT={status['verdict']}")
    print("TODAY_CLOSED_PNL_STATUS_V1_OK")


def html_page(status: dict[str, Any]) -> str:
    def esc(v: Any) -> str:
        return html.escape(str(v))

    rows = "\n".join(
        f"""
        <tr>
          <td>{esc(r['symbol'])}</td>
          <td>{esc(r['strategy'])}</td>
          <td>{esc(r['timeframe'])}</td>
          <td>{r['trades']}</td>
          <td>{r['buy_trades']}</td>
          <td>{r['sell_trades']}</td>
          <td>{r['closed_cycles']}</td>
          <td>{r['open_qty']:.4f}</td>
          <td>{r['gross_pnl']:.6f}</td>
          <td>{r['commission']:.6f}</td>
          <td>{r['net_pnl']:.6f}</td>
        </tr>
        """
        for r in status["summaries"]
    )

    cycles = "\n".join(
        f"""
        <tr>
          <td>{esc(c['close_time'])}</td>
          <td>{esc(c['symbol'])}</td>
          <td>{esc(c['strategy'])}</td>
          <td>{c['qty']:.4f}</td>
          <td>{c['open_price']:.6f}</td>
          <td>{c['close_price']:.6f}</td>
          <td>{c['gross_pnl']:.6f}</td>
          <td>{c['net_pnl']:.6f}</td>
        </tr>
        """
        for c in status["recent_closed_cycles"]
    )

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="15">
  <title>TODAY_CLOSED_PNL_STATUS_V1</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #111; color: #eee; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border: 1px solid #444; padding: 6px 8px; text-align: right; }}
    th {{ background: #222; }}
    td:first-child, th:first-child, td:nth-child(2), th:nth-child(2), td:nth-child(3), th:nth-child(3) {{ text-align: left; }}
    .ok {{ color: #8ee68e; }}
    .warn {{ color: #ffd166; }}
    .metric {{ display: inline-block; margin-right: 24px; }}
    a {{ color: #8ab4ff; }}
  </style>
</head>
<body>
  <h1>TODAY_CLOSED_PNL_STATUS_V1</h1>
  <p>
    <span class="metric">generated_at: {esc(status['generated_at'])}</span>
    <span class="metric">runtime_allow: 0</span>
    <span class="metric">execution_enabled: 0</span>
    <span class="metric">real_trading_enabled: 0</span>
    <a href="/json">JSON</a>
  </p>

  <h2>Сводка</h2>
  <p>
    <span class="metric">trades_today: {status['trades_today']}</span>
    <span class="metric">symbols: {status['symbols']}</span>
    <span class="metric">closed_cycles: {status['closed_cycles']}</span>
    <span class="metric">gross_pnl: {status['gross_pnl']:.6f}</span>
    <span class="metric">commission: {status['commission']:.6f}</span>
    <span class="metric">net_pnl: {status['net_pnl']:.6f}</span>
    <span class="metric">context_clean: {status['context_clean']}</span>
  </p>
  <p class="ok">VERDICT={esc(status['verdict'])}</p>

  <h2>По инструментам</h2>
  <table>
    <thead>
      <tr>
        <th>symbol</th><th>strategy</th><th>timeframe</th>
        <th>trades</th><th>BUY</th><th>SELL</th><th>closed</th>
        <th>open_qty</th><th>gross</th><th>commission</th><th>net</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Последние закрытые циклы</h2>
  <table>
    <thead>
      <tr>
        <th>close_time</th><th>symbol</th><th>strategy</th>
        <th>qty</th><th>open_price</th><th>close_price</th><th>gross</th><th>net</th>
      </tr>
    </thead>
    <tbody>{cycles}</tbody>
  </table>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        status = build_status()

        if parsed.path == "/json":
            body = json.dumps(status, ensure_ascii=False, indent=2).encode("utf-8")
            self._send(body, "application/json; charset=utf-8")
            return

        body = html_page(status).encode("utf-8")
        self._send(body, "text/html; charset=utf-8")


def serve(host: str, port: int) -> None:
    print("=== TODAY CLOSED PNL STATUS V1 SERVER ===")
    print(f"listen={host}:{port}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("TODAY_CLOSED_PNL_STATUS_V1_SERVER_OK")
    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--host", default=os.getenv("TODAY_CLOSED_PNL_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("TODAY_CLOSED_PNL_PORT", "8088")))
    args = parser.parse_args()

    if args.serve:
        serve(args.host, args.port)
        return 0

    print_cli(build_status())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
