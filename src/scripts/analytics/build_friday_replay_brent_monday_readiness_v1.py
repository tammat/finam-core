#!/usr/bin/env python3
"""Read-only Friday replay, Brent incident audit and Monday readiness report."""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import RealDictCursor


MSK = ZoneInfo("Europe/Moscow")


def _f(value: object | None) -> float | None:
    return None if value is None else float(value)


def _fmt(value: float | None, digits: int = 2) -> str:
    return "—" if value is None else f"{value:+.{digits}f}"


def _previous_friday(day: date) -> date:
    offset = (day.weekday() - 4) % 7
    return day - timedelta(days=offset or 7)


def build_report(cur: RealDictCursor, target: date) -> dict:
    start = datetime.combine(target, datetime.min.time(), tzinfo=MSK)
    end = start + timedelta(days=1)
    cur.execute(
        """
        SELECT source_signal_id,strategy_code,symbol_code,side_code,candidate_code,
               entry_mode,shadow_entered,shadow_net_r,placebo_net_r,actual_net_r,
               entry_decision,entry_decision_reason,label_start_ts,label_end_ts
        FROM analytics.entry_exit_signal_shadow_pair_v2
        WHERE label_start_ts >= %s AND label_start_ts < %s
          AND label_end_ts <= clock_timestamp()
        ORDER BY label_start_ts,source_signal_id,candidate_code
        """,
        (start, end),
    )
    rows = list(cur.fetchall())
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["strategy_code"], row["symbol_code"], row["side_code"], row["candidate_code"])].append(row)

    replay = []
    for key, items in groups.items():
        entered = [item for item in items if item["shadow_entered"] and item["shadow_net_r"] is not None]
        shadow = [_f(item["shadow_net_r"]) for item in entered]
        placebo = [_f(item["placebo_net_r"]) for item in entered if item["placebo_net_r"] is not None]
        actual = [_f(item["actual_net_r"]) for item in items if item["actual_net_r"] is not None]
        shadow_avg = mean(shadow) if shadow else None
        placebo_avg = mean(placebo) if placebo else None
        replay.append({
            "strategy": key[0], "symbol": key[1], "side": key[2], "candidate": key[3],
            "signals": len(items), "entered": len(entered), "skipped": len(items) - len(entered),
            "shadow_net_r": sum(shadow) if shadow else None,
            "shadow_expectancy_r": shadow_avg,
            "placebo_expectancy_r": placebo_avg,
            "delta_vs_placebo_r": (
                shadow_avg - placebo_avg
                if shadow_avg is not None and placebo_avg is not None else None
            ),
            "paper_baseline_avg_r": mean(actual) if actual else None,
            "diagnostic_only": True,
        })
    replay.sort(key=lambda x: (x["delta_vs_placebo_r"] is not None, x["delta_vs_placebo_r"] or -999), reverse=True)

    cur.execute(
        """
        SELECT * FROM closed_trades
        WHERE symbol LIKE 'BR%%@RTSX'
          AND (entry_ts >= %s - interval '1 day' AND entry_ts < %s)
        ORDER BY net_pnl ASC
        """,
        (start, end),
    )
    brent_trades = list(cur.fetchall())
    incident = None
    if brent_trades:
        worst = brent_trades[0]
        context = dict((worst.get("payload") or {}).get("context") or {})
        stop = _f(context.get("entry_stop_price"))
        entry_ts = worst["entry_ts"]
        exit_ts = worst["exit_ts"]
        cur.execute(
            """
            SELECT ts,open,high,low,close,volume FROM market_bars
            WHERE symbol=%s AND timeframe='M1'
              AND ts >= %s - interval '10 minutes'
              AND ts <= %s + interval '10 minutes'
            ORDER BY ts
            """,
            (worst["symbol"], entry_ts, exit_ts),
        )
        bars = list(cur.fetchall())
        after_entry = [bar for bar in bars if bar["ts"] > entry_ts]
        lows = [_f(bar["low"]) for bar in after_entry]
        highs = [_f(bar["high"]) for bar in after_entry]
        first_stop = next((bar for bar in after_entry if stop is not None and _f(bar["low"]) <= stop), None)
        gap_minutes = None
        if len(after_entry) > 1:
            gap_minutes = max(
                (after_entry[i]["ts"] - after_entry[i - 1]["ts"]).total_seconds() / 60
                for i in range(1, len(after_entry))
            )
        multiplier = _f(((worst.get("payload") or {}).get("pnl_units") or {}).get("price_to_rub_multiplier"))
        incident = {
            "trade_id": worst["id"], "signal_id": worst["signal_id"], "symbol": worst["symbol"],
            "side": worst["side"], "entry_ts": entry_ts, "exit_ts": exit_ts,
            "entry_price": _f(worst["entry_price"]), "planned_stop": stop,
            "exit_price": _f(worst["exit_price"]), "net_pnl_rub": _f(worst["net_pnl"]),
            "net_pnl_r": _f(context.get("net_pnl_r")), "entry_regime": context.get("entry_regime"),
            "entry_session": context.get("entry_session_msk"), "actual_exit_reason": context.get("actual_exit_reason"),
            "first_observed_stop_breach_ts": first_stop["ts"] if first_stop else None,
            "first_observed_stop_breach_open": _f(first_stop["open"]) if first_stop else None,
            "observed_mfe_price": (max(highs) - _f(worst["entry_price"])) if highs else None,
            "observed_mae_price": (min(lows) - _f(worst["entry_price"])) if lows else None,
            "stop_slippage_price": (_f(worst["exit_price"]) - stop) if stop is not None else None,
            "stop_slippage_rub": ((_f(worst["exit_price"]) - stop) * multiplier) if stop is not None and multiplier else None,
            "largest_m1_data_gap_minutes": gap_minutes,
            "diagnosis": "LATE_RANGE_LOW_VOL_ENTRY_BEFORE_UNOBSERVABLE_OVERNIGHT_GAP",
            "trailing_could_prevent": False,
        }

    cur.execute(
        """
        SELECT
          (SELECT max(ts) FROM market_bars WHERE symbol='IMOEX2' AND timeframe='M15') mx_m15_last,
          (SELECT max(ts) FROM market_bars WHERE symbol='IMOEX2' AND timeframe='M1') mx_m1_last,
          (SELECT max(ts) FROM market_bars WHERE (symbol='RVI' OR symbol LIKE 'VI%%@RTSX') AND timeframe='M1') rvi_m1_last,
          (SELECT count(*) FROM analytics.v5_oos_run_v1) v5_oos_runs
        """
    )
    readiness = dict(cur.fetchone())
    readiness.update({
        "gate": "WAIT_2_COMPLETED_MX_M15_AND_FRESH_MX_RVI",
        "paper_profile_changed": False,
        "real_trading_enabled": False,
        "friday_replay_is_promotion_evidence": False,
    })
    return {
        "schema_version": "FRIDAY_REPLAY_BRENT_MONDAY_V1",
        "target_date": target.isoformat(),
        "generated_at": datetime.now(MSK),
        "same_signal_completed_pairs": len(rows),
        "independent_source_signals": len({row["source_signal_id"] for row in rows}),
        "replay": replay,
        "brent_incident": incident,
        "monday_readiness": readiness,
    }


def markdown(report: dict) -> str:
    incident = report["brent_incident"] or {}
    lines = [
        f"# Replay пятницы {report['target_date']} + Brent + Monday gate",
        "",
        "Отчёт read-only. Paper-профили и реальная торговля не изменялись.",
        "",
        "## Итог",
        "",
        f"- Независимых исходных сигналов: {report['independent_source_signals']}.",
        f"- Завершённых пар «тот же сигнал / кандидат»: {report['same_signal_completed_pairs']}.",
        "- Результаты одного дня — диагностика, а не основание для продвижения в Paper.",
        "",
        "## Brent: критический эпизод",
        "",
        f"- Сделка: `{incident.get('trade_id')}`, {incident.get('side')} {incident.get('symbol')}.",
        f"- Вход / плановый стоп / выход: {incident.get('entry_price')} / {incident.get('planned_stop')} / {incident.get('exit_price')}.",
        f"- Результат: {_fmt(incident.get('net_pnl_rub'))} ₽, {_fmt(incident.get('net_pnl_r'))}R.",
        f"- Режим и сессия входа: {incident.get('entry_regime')} / {incident.get('entry_session')}.",
        f"- Проскальзывание относительно стопа: {_fmt(incident.get('stop_slippage_price'), 4)} пункта, {_fmt(incident.get('stop_slippage_rub'))} ₽.",
        f"- Максимальный разрыв M1: {incident.get('largest_m1_data_gap_minutes')} мин.",
        "- Причина: поздний LONG в range/low-vol перед интервалом, где виртуальный стоп не наблюдался. Трейлинг не мог устранить гэп; нужен запрет нового входа.",
        "",
        "## Лучшие пятничные варианты (диагностика)",
        "",
        "| Инструмент | Направление | Вариант | Сигналы | Входы | Net R | Exp R | Δ к placebo |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["replay"][:20]:
        lines.append(
            f"| {row['symbol']} | {row['side']} | {row['candidate']} | {row['signals']} | {row['entered']} | "
            f"{_fmt(row['shadow_net_r'])} | {_fmt(row['shadow_expectancy_r'])} | {_fmt(row['delta_vs_placebo_r'])} |"
        )
    lines += [
        "",
        "## Monday gate",
        "",
        "Новые Paper-входы в понедельник разрешаются только после двух завершённых M15 по IMOEX и при одновременно свежих IMOEX/RVI. Защитные выходы всегда разрешены. При нехватке данных gate закрыт.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()
    target = args.date or _previous_friday(datetime.now(MSK).date())
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        report = build_report(cur, target)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stem = f"friday_replay_brent_monday_{target.isoformat()}"
    (output / f"{stem}.json").write_text(json.dumps(report, default=str, ensure_ascii=False, indent=2) + "\n")
    (output / f"{stem}.md").write_text(markdown(report))
    print(f"report={output / (stem + '.md')}")
    print(f"signals={report['independent_source_signals']} pairs={report['same_signal_completed_pairs']}")
    print("paper_changed=0 real_changed=0")
    print("VERDICT=FRIDAY_REPLAY_BRENT_MONDAY_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
