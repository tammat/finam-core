from __future__ import annotations

import html
import json
import os
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TODAY_CLOSED_PNL_WIDGET_V1 — read-only HTML/JSON widget для существующего dashboard 8088.
# Ничего не меняет в БД, runtime, execution и real trading.


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
    origin
from trades
where created_at::date = current_date
  and coalesce(is_invalid, false) = false
order by created_at asc, id asc;
"""


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
    qty: float
    open_price: float
    close_price: float
    gross_pnl: float
    commission: float
    net_pnl: float


def _s(v: Any, default: str = "") -> str:
    if v is None:
        return default
    return str(v).strip()


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default


def fetch_today_trades() -> list[TradeRow]:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is required")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(TRADES_SQL)
            rows = cur.fetchall()

    out: list[TradeRow] = []
    for r in rows:
        out.append(
            TradeRow(
                id=int(r.get("id") or 0),
                created_at=str(r.get("created_at")),
                symbol=_s(r.get("symbol"), "UNKNOWN"),
                strategy=_s(r.get("strategy"), "UNKNOWN"),
                timeframe=_s(r.get("timeframe"), "UNKNOWN"),
                side=_s(r.get("side"), "UNKNOWN").upper(),
                qty=_f(r.get("qty")),
                price=_f(r.get("price")),
                commission=_f(r.get("commission")),
                trade_source=_s(r.get("trade_source")),
                origin=_s(r.get("origin")),
            )
        )
    return out


def reconstruct_closed_cycles(trades: list[TradeRow]) -> tuple[list[ClosedCycle], dict[tuple[str, str, str], float]]:
    inventory: dict[tuple[str, str, str], deque[TradeRow]] = defaultdict(deque)
    open_tail: dict[tuple[str, str, str], float] = defaultdict(float)
    closed: list[ClosedCycle] = []

    for trade in trades:
        key = (trade.symbol, trade.strategy or "UNKNOWN", trade.timeframe or "UNKNOWN")
        qty_left = trade.qty

        if qty_left <= 0:
            continue

        if trade.side in ("BUY", "LONG"):
            inventory[key].append(trade)
            open_tail[key] += qty_left
            continue

        if trade.side in ("SELL", "SHORT"):
            while qty_left > 1e-12 and inventory[key]:
                opened = inventory[key][0]
                q = min(qty_left, opened.qty)

                gross = (trade.price - opened.price) * q
                commission = (opened.commission + trade.commission) * (q / max(trade.qty, 1e-12))
                net = gross - commission

                closed.append(
                    ClosedCycle(
                        symbol=trade.symbol,
                        strategy=trade.strategy or "UNKNOWN",
                        timeframe=trade.timeframe or "UNKNOWN",
                        open_time=opened.created_at,
                        close_time=trade.created_at,
                        qty=q,
                        open_price=opened.price,
                        close_price=trade.price,
                        gross_pnl=gross,
                        commission=commission,
                        net_pnl=net,
                    )
                )

                opened.qty -= q
                qty_left -= q
                open_tail[key] -= q

                if opened.qty <= 1e-12:
                    inventory[key].popleft()

            if qty_left > 1e-12:
                open_tail[key] -= qty_left

    return closed, dict(open_tail)


def build_today_closed_pnl_status_v1() -> dict[str, Any]:
    trades = fetch_today_trades()
    closed, open_tail = reconstruct_closed_cycles([TradeRow(**asdict(t)) for t in trades])

    grouped: dict[tuple[str, str, str], list[TradeRow]] = defaultdict(list)
    for t in trades:
        grouped[(t.symbol, t.strategy or "UNKNOWN", t.timeframe or "UNKNOWN")].append(t)

    closed_by_key: dict[tuple[str, str, str], list[ClosedCycle]] = defaultdict(list)
    for c in closed:
        closed_by_key[(c.symbol, c.strategy, c.timeframe)].append(c)

    summaries: list[dict[str, Any]] = []
    for key, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        cycles = closed_by_key.get(key, [])
        gross = sum(c.gross_pnl for c in cycles)
        commission = sum(c.commission for c in cycles)
        net = sum(c.net_pnl for c in cycles)
        symbol, strategy, timeframe = key

        summaries.append(
            {
                "symbol": symbol,
                "strategy": strategy,
                "timeframe": timeframe,
                "trades": len(rows),
                "buy_trades": sum(1 for t in rows if t.side in ("BUY", "LONG")),
                "sell_trades": sum(1 for t in rows if t.side in ("SELL", "SHORT")),
                "closed_cycles": len(cycles),
                "closed_qty": sum(c.qty for c in cycles),
                "open_qty": open_tail.get(key, 0.0),
                "gross_pnl": gross,
                "commission": commission,
                "net_pnl": net,
                "first_trade": rows[0].created_at,
                "last_trade": rows[-1].created_at,
            }
        )

    context_clean = all(t.symbol and t.strategy and t.timeframe for t in trades)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_allow": 0,
        "execution_enabled": 0,
        "real_trading_enabled": 0,
        "db_update": 0,
        "trades_today": len(trades),
        "symbols": len(summaries),
        "closed_cycles": len(closed),
        "gross_pnl": sum(r["gross_pnl"] for r in summaries),
        "commission": sum(r["commission"] for r in summaries),
        "net_pnl": sum(r["net_pnl"] for r in summaries),
        "context_clean": 1 if context_clean else 0,
        "summaries": summaries,
        "recent_closed_cycles": [asdict(c) for c in sorted(closed, key=lambda x: x.close_time, reverse=True)[:20]],
        "verdict": "TODAY_CLOSED_PNL_STATUS_OK" if context_clean else "TODAY_CLOSED_PNL_CONTEXT_HAS_GAPS",
    }


def render_today_closed_pnl_html_v1() -> str:
    status = build_today_closed_pnl_status_v1()

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

    return f"""
<div class="card">
  <h2>TODAY_CLOSED_PNL_STATUS_V1</h2>
  <p class="muted">
    Read-only. runtime_allow=0 | execution_enabled=0 | real_trading_enabled=0 |
    <a href="/today-pnl/json">JSON</a>
  </p>
  <table>
    <tr><th>Сделок</th><th>Закрытых циклов</th><th>Gross PnL</th><th>Commission</th><th>Net PnL</th><th>Контекст</th></tr>
    <tr>
      <td>{status['trades_today']}</td>
      <td>{status['closed_cycles']}</td>
      <td>{status['gross_pnl']:.6f}</td>
      <td>{status['commission']:.6f}</td>
      <td>{status['net_pnl']:.6f}</td>
      <td>{status['context_clean']}</td>
    </tr>
  </table>

  <h3>По инструментам</h3>
  <table>
    <tr>
      <th>symbol</th><th>strategy</th><th>timeframe</th><th>trades</th><th>BUY</th><th>SELL</th>
      <th>closed</th><th>open_qty</th><th>gross</th><th>commission</th><th>net</th>
    </tr>
    {rows}
  </table>

  <h3>Последние закрытые циклы</h3>
  <table>
    <tr>
      <th>close_time</th><th>symbol</th><th>strategy</th><th>qty</th><th>open</th><th>close</th><th>gross</th><th>net</th>
    </tr>
    {cycles}
  </table>
</div>
"""


def render_today_closed_pnl_page_v1() -> str:
    body = render_today_closed_pnl_html_v1()
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="15">
  <title>TODAY_CLOSED_PNL_STATUS_V1</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f7; color: #222; }}
    h1, h2 {{ margin-bottom: 8px; }}
    .card {{ background: white; padding: 16px; margin-bottom: 18px; border-radius: 10px; box-shadow: 0 1px 4px #ddd; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid #e5e5e5; text-align: left; }}
    th {{ background: #efefef; }}
    .muted {{ color: #666; }}
    a {{ color: #2563eb; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>FINAM_CORE V3 — Today PnL</h1>
    <p><a href="/">Назад</a> | <a href="/today-pnl/json">JSON</a></p>
  </div>
  {body}
</body>
</html>
"""


def render_today_closed_pnl_json_v1() -> str:
    return json.dumps(build_today_closed_pnl_status_v1(), ensure_ascii=False, indent=2)
