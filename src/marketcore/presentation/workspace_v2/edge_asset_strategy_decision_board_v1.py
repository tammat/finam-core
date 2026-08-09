#!/usr/bin/env python3
"""
EDGE_ASSET_STRATEGY_DECISION_BOARD_V1

Read-only read-model для Edge OOS Control Center.

Критическое разделение:
- asset_status: инструмент остаётся доступным для research;
- strategy_status: решение по конкретной стратегии/гипотезе.

Никаких изменений runtime/execution.
"""

from __future__ import annotations

import html
import json
import os
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras


GOLD_CONFIG = Path("config/research/gold_up_regime_frozen_v1.json")


def _dec(value) -> Decimal:
    return Decimal(str(value or 0))


def _pf(gross_profit, gross_loss):
    gp = _dec(gross_profit)
    gl = abs(_dec(gross_loss))
    return gp / gl if gl > 0 else None


def _clean_chain_metrics(cur, symbol_prefix: str, strategy_like: str) -> dict:
    cur.execute(
        """
        SELECT
            count(*) AS trades,
            coalesce(sum(net_pnl),0)::numeric AS net_pnl,
            coalesce(avg(net_pnl),0)::numeric AS expectancy,
            coalesce(sum(CASE WHEN net_pnl>0 THEN net_pnl ELSE 0 END),0)::numeric
                AS gross_profit,
            abs(
                coalesce(
                    sum(CASE WHEN net_pnl<0 THEN net_pnl ELSE 0 END),
                    0
                )
            )::numeric AS gross_loss
        FROM closed_trade_chains_v3
        WHERE symbol LIKE %s
          AND strategy LIKE %s
          AND timeframe='M5'
          AND quality_status='FULL'
        """,
        (symbol_prefix, strategy_like),
    )

    row = dict(cur.fetchone() or {})

    pf = _pf(
        row.get("gross_profit"),
        row.get("gross_loss"),
    )

    return {
        "trades": int(row.get("trades") or 0),
        "net_pnl": _dec(row.get("net_pnl")),
        "expectancy": _dec(row.get("expectancy")),
        "profit_factor": pf,
    }


def _gold_oos(cur) -> dict:
    if not GOLD_CONFIG.exists():
        return {
            "available": False,
            "trades": 0,
            "minimum": 0,
            "expectancy": None,
            "profit_factor": None,
            "status": "NO_FROZEN_CONFIG",
            "reason": "gold_frozen_config_missing",
        }

    cfg = json.loads(GOLD_CONFIG.read_text())

    boundary = cfg["freeze_boundary_exclusive"]
    minimum = int(cfg["oos_policy"]["minimum_oos_trades"])
    min_pf = Decimal(str(cfg["oos_policy"]["pass_profit_factor_gte"]))

    cur.execute(
        """
        WITH candidates AS (
            SELECT
                s.signal_ts,
                s.side,
                s.entry_price::numeric AS entry_price,
                exit_bar.exit_price,
                ctx.sma20,
                ctx.sma50
            FROM runtime_shadow_gold_signals s

            LEFT JOIN LATERAL (
                SELECT b.close::numeric AS exit_price
                FROM market_bars b
                WHERE b.symbol=s.symbol
                  AND b.timeframe=s.timeframe
                  AND b.ts>s.signal_ts
                ORDER BY b.ts
                OFFSET 9
                LIMIT 1
            ) exit_bar ON true

            LEFT JOIN LATERAL (
                SELECT q.sma20,q.sma50
                FROM (
                    SELECT
                        b.ts,
                        avg(b.close::numeric) OVER (
                            ORDER BY b.ts
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) AS sma20,
                        avg(b.close::numeric) OVER (
                            ORDER BY b.ts
                            ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
                        ) AS sma50
                    FROM market_bars b
                    WHERE b.symbol=s.symbol
                      AND b.timeframe=s.timeframe
                      AND b.ts<=s.signal_ts
                    ORDER BY b.ts DESC
                    LIMIT 60
                ) q
                ORDER BY q.ts DESC
                LIMIT 1
            ) ctx ON true

            WHERE s.symbol=%s
              AND s.strategy=%s
              AND s.signal_ts>%s::timestamptz
        ),
        scored AS (
            SELECT
                CASE
                    WHEN exit_price IS NULL THEN NULL
                    WHEN side='SELL' THEN entry_price-exit_price
                    ELSE exit_price-entry_price
                END AS pnl
            FROM candidates
            WHERE sma20>sma50
        )
        SELECT
            count(*) FILTER (WHERE pnl IS NOT NULL) AS trades,
            coalesce(sum(pnl) FILTER (WHERE pnl IS NOT NULL),0)::numeric AS net_pnl,
            coalesce(avg(pnl) FILTER (WHERE pnl IS NOT NULL),0)::numeric AS expectancy,
            coalesce(sum(CASE WHEN pnl>0 THEN pnl ELSE 0 END),0)::numeric
                AS gross_profit,
            abs(
                coalesce(
                    sum(CASE WHEN pnl<0 THEN pnl ELSE 0 END),
                    0
                )
            )::numeric AS gross_loss
        FROM scored
        """,
        (
            cfg["symbol"],
            cfg["strategy"],
            boundary,
        ),
    )

    row = dict(cur.fetchone() or {})

    trades = int(row.get("trades") or 0)
    expectancy = _dec(row.get("expectancy"))
    pf = _pf(
        row.get("gross_profit"),
        row.get("gross_loss"),
    )

    if trades < minimum:
        status = "ACCUMULATING"
        reason = "prospective_oos_sample_below_minimum"
    elif expectancy > 0 and pf is not None and pf >= min_pf:
        status = "OOS_PASS"
        reason = "prospective_oos_thresholds_passed"
    else:
        status = "OOS_FAIL"
        reason = "prospective_oos_thresholds_failed"

    return {
        "available": True,
        "trades": trades,
        "minimum": minimum,
        "expectancy": expectancy,
        "profit_factor": pf,
        "status": status,
        "reason": reason,
        "freeze_boundary": boundary,
        "development_pf": cfg.get("development_up_profit_factor"),
        "development_expectancy": cfg.get(
            "development_up_expectancy"
        ),
    }


def load_edge_asset_strategy_decisions_v1() -> list[dict]:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            gold = _gold_oos(cur)

            br = _clean_chain_metrics(
                cur,
                "BR%@RTSX",
                "BR_CONSERVATIVE_BREAKOUT",
            )

            ng = _clean_chain_metrics(
                cur,
                "NG%@RTSX",
                "NG_CONSERVATIVE_BREAKOUT%",
            )

        rows = []

        rows.append({
            "asset_code": "GOLD",
            "asset_name": "Золото",
            "asset_status": "RESEARCH_ACTIVE",
            "strategy": "GOLD_UP_REGIME_FROZEN_V1",
            "stage": "PROSPECTIVE_OOS",
            "sample": f"{gold['trades']}/{gold['minimum']}",
            "profit_factor": gold["profit_factor"],
            "expectancy": gold["expectancy"],
            "strategy_status": gold["status"],
            "reason": gold["reason"],
            "promotion": "BLOCKED",
        })

        br_reject = (
            br["trades"] > 0
            and br["expectancy"] < 0
            and br["profit_factor"] is not None
            and br["profit_factor"] < 1
        )

        rows.append({
            "asset_code": "BR",
            "asset_name": "Brent",
            "asset_status": "RESEARCH_ACTIVE",
            "strategy": "BR_CONSERVATIVE_BREAKOUT",
            "stage": "CLEAN_FULL_CHAIN_REVIEW",
            "sample": str(br["trades"]),
            "profit_factor": br["profit_factor"],
            "expectancy": br["expectancy"],
            "strategy_status": (
                "REJECT"
                if br_reject
                else "REVIEW"
            ),
            "reason": (
                "negative_clean_full_chain_edge"
                if br_reject
                else "clean_chain_review_required"
            ),
            "promotion": "BLOCKED",
        })

        ng_reject = (
            ng["trades"] > 0
            and ng["expectancy"] < 0
            and ng["profit_factor"] is not None
            and ng["profit_factor"] < 1
        )

        rows.append({
            "asset_code": "NG",
            "asset_name": "Природный газ",
            "asset_status": "RESEARCH_ACTIVE",
            "strategy": "NG_CONSERVATIVE_BREAKOUT*",
            "stage": "CLEAN_FULL_CHAIN_REVIEW",
            "sample": str(ng["trades"]),
            "profit_factor": ng["profit_factor"],
            "expectancy": ng["expectancy"],
            "strategy_status": (
                "REJECT"
                if ng_reject
                else "REVIEW"
            ),
            "reason": (
                "negative_clean_full_chain_edge"
                if ng_reject
                else "clean_chain_review_required"
            ),
            "promotion": "BLOCKED",
        })

        conn.rollback()
        return rows

    finally:
        conn.close()


def render_edge_asset_strategy_decision_board_v1() -> str:
    rows = load_edge_asset_strategy_decisions_v1()

    body = []

    for row in rows:
        pf = row["profit_factor"]
        exp = row["expectancy"]

        pf_text = "—" if pf is None else f"{float(pf):.3f}"
        exp_text = "—" if exp is None else f"{float(exp):+.4f}"

        status = str(row["strategy_status"])
        css = (
            "pass"
            if status == "OOS_PASS"
            else "fail"
            if status in {"REJECT", "OOS_FAIL"}
            else ""
        )

        body.append(
            "<tr>"
            f"<td><b>{html.escape(row['asset_name'])}</b></td>"
            f"<td>{html.escape(row['asset_status'])}</td>"
            f"<td>{html.escape(row['strategy'])}</td>"
            f"<td>{html.escape(row['stage'])}</td>"
            f"<td>{html.escape(row['sample'])}</td>"
            f"<td>{pf_text}</td>"
            f"<td class=\"{'is-positive' if exp is not None and exp > 0 else 'is-negative'}\">"
            f"{exp_text}</td>"
            f"<td><span class=\"mc-oos-badge {css}\">"
            f"{html.escape(status)}</span></td>"
            f"<td>{html.escape(row['reason'])}</td>"
            f"<td>{html.escape(row['promotion'])}</td>"
            "</tr>"
        )

    return f"""
    <section id="asset-strategy-decisions"
             class="mc-oos-panel mc-edge-research-panel">
      <div class="mc-oos-toolbar">
        <div>
          <p class="mc-edge-eyebrow">ASSET / STRATEGY DECISIONS</p>
          <h2>Решения по инструментам и стратегиям</h2>
          <p>Статус инструмента отделён от статуса конкретной стратегии.</p>
        </div>
      </div>

      <div class="mc-oos-table-wrap">
        <table class="mc-oos-table">
          <thead>
            <tr>
              <th>Инструмент</th>
              <th>Asset status</th>
              <th>Стратегия / гипотеза</th>
              <th>Этап</th>
              <th>Sample</th>
              <th>PF</th>
              <th>Expectancy</th>
              <th>Решение</th>
              <th>Причина</th>
              <th>Promotion</th>
            </tr>
          </thead>
          <tbody>
            {''.join(body)}
          </tbody>
        </table>
      </div>
    </section>
    """
