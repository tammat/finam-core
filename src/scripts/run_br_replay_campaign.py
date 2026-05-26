#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class CampaignWindow:
    index: int
    from_ts: datetime
    to_ts: datetime


def parse_dt(value: str) -> datetime:
    # Русский комментарий: поддерживаем YYYY-MM-DD и ISO datetime.
    if len(value) == 10:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_windows(start: datetime, end: datetime, days: int) -> list[CampaignWindow]:
    windows: list[CampaignWindow] = []
    cursor = start
    idx = 1

    while cursor < end:
        to_ts = min(cursor + timedelta(days=days), end)
        windows.append(CampaignWindow(index=idx, from_ts=cursor, to_ts=to_ts))
        cursor = to_ts
        idx += 1

    return windows


def run_cmd(cmd: list[str], env: dict[str, str]) -> str:
    proc = subprocess.run(
        cmd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if proc.returncode != 0:
        print(proc.stdout, flush=True)
        raise SystemExit(proc.returncode)

    return proc.stdout


def parse_replay_stats(output: str) -> dict[str, str]:
    stats: dict[str, str] = {}

    for line in output.splitlines():
        if line.startswith("SYMBOL_STATS "):
            for token in line.split()[1:]:
                if "=" in token:
                    k, v = token.split("=", 1)
                    stats[k] = v

    return stats


def extract_new_trade_ids(before_max_id: int, after_max_id: int) -> tuple[str, str]:
    if after_max_id <= before_max_id:
        return "", ""
    return str(before_max_id + 1), str(after_max_id)


def get_max_trade_id(database_url: str, symbol: str) -> int:
    sql = (
        "select coalesce(max(id), 0) "
        f"from trades where symbol = '{symbol}' and trade_source = 'paper';"
    )
    out = run_cmd(["psql", database_url, "-t", "-A", "-c", sql], env=os.environ.copy())
    return int(out.strip() or "0")


def parse_pnl_summary(output: str) -> dict[str, str]:
    result: dict[str, str] = {}

    for line in output.splitlines():
        if line.startswith("CLOSED_TRADES "):
            for token in line.split()[1:]:
                if "=" in token:
                    k, v = token.split("=", 1)
                    result[k] = v

    return result




def save_campaign_window(
    database_url: str,
    campaign_id: str,
    symbol: str,
    strategy: str,
    timeframe: str,
    window_index: int,
    from_ts: datetime,
    to_ts: datetime,
    replay_stats: dict[str, str],
    pnl_stats: dict[str, str],
    min_id: str,
    max_id: str,
) -> None:
    import psycopg

    sql = """
    insert into replay_campaign_runs (
        campaign_id, replay_id, symbol, strategy, timeframe, status,
        started_at, finished_at, duration_sec, return_code, command, raw_json,
        from_ts, to_ts, window_index,
        signals, paper_orders, trades_logged,
        min_trade_id, max_trade_id,
        closed_trades, net_pnl, winrate
    )
    values (
        %(campaign_id)s, %(replay_id)s, %(symbol)s, %(strategy)s, %(timeframe)s, %(status)s,
        %(started_at)s, %(finished_at)s, %(duration_sec)s, %(return_code)s, %(command)s, %(raw_json)s,
        %(from_ts)s, %(to_ts)s, %(window_index)s,
        %(signals)s, %(paper_orders)s, %(trades_logged)s,
        %(min_trade_id)s, %(max_trade_id)s,
        %(closed_trades)s, %(net_pnl)s, %(winrate)s
    )
    on conflict (campaign_id, symbol, window_index)
    do update set
        signals = excluded.signals,
        paper_orders = excluded.paper_orders,
        trades_logged = excluded.trades_logged,
        min_trade_id = excluded.min_trade_id,
        max_trade_id = excluded.max_trade_id,
        closed_trades = excluded.closed_trades,
        net_pnl = excluded.net_pnl,
        winrate = excluded.winrate,
        from_ts = excluded.from_ts,
        to_ts = excluded.to_ts;
    """

    params = {
        "campaign_id": campaign_id,
        "replay_id": f"{campaign_id}_{symbol}_{window_index}",
        "status": "OK",
        "started_at": from_ts,
        "finished_at": to_ts,
        "duration_sec": max((to_ts - from_ts).total_seconds(), 0.0),
        "return_code": 0,
        "command": "run_br_replay_campaign.py",
        "raw_json": "{}",
        "symbol": symbol,
        "strategy": strategy,
        "timeframe": timeframe,
        "from_ts": from_ts,
        "to_ts": to_ts,
        "window_index": window_index,
        "signals": int(replay_stats.get("signals_generated", "0") or "0"),
        "paper_orders": int(replay_stats.get("paper_orders", "0") or "0"),
        "trades_logged": int(replay_stats.get("trades_logged", "0") or "0"),
        "min_trade_id": int(min_id) if min_id else None,
        "max_trade_id": int(max_id) if max_id else None,
        "closed_trades": int(pnl_stats.get("closed", "0") or "0"),
        "net_pnl": float(pnl_stats.get("net", "0") or "0"),
        "winrate": float(pnl_stats.get("winrate", "0") or "0"),
    }

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--from-ts", required=True)
    parser.add_argument("--to-ts", required=True)
    parser.add_argument("--window-days", type=int, default=3)
    parser.add_argument("--campaign-id", default="br_replay_campaign")
    parser.add_argument("--disable-runtime-control", action="store_true", default=True)
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    start = parse_dt(args.from_ts)
    end = parse_dt(args.to_ts)
    windows = build_windows(start, end, args.window_days)

    print(
        "BR_REPLAY_CAMPAIGN_START",
        f"symbol={args.symbol}",
        f"from_ts={start.isoformat()}",
        f"to_ts={end.isoformat()}",
        f"windows={len(windows)}",
        flush=True,
    )

    total_trades = 0
    total_net = 0.0

    for window in windows:
        before_id = get_max_trade_id(database_url, args.symbol)

        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        env["REPLAY_DISABLE_RUNTIME_CONTROL"] = "1"
        env["REPLAY_CAMPAIGN_ID"] = args.campaign_id

        replay_out = run_cmd(
            [
                sys.executable,
                "src/scripts/replay_br_pipeline.py",
                "--symbol",
                args.symbol,
                "--from-ts",
                window.from_ts.isoformat(),
                "--to-ts",
                window.to_ts.isoformat(),
            ],
            env=env,
        )

        after_id = get_max_trade_id(database_url, args.symbol)
        min_id, max_id = extract_new_trade_ids(before_id, after_id)
        replay_stats = parse_replay_stats(replay_out)

        pnl_stats: dict[str, str] = {}
        if min_id and max_id:
            pnl_env = os.environ.copy()
            pnl_env["PYTHONPATH"] = "src"
            pnl_env["SYMBOL"] = args.symbol
            pnl_env["MIN_ID"] = min_id
            pnl_env["MAX_ID"] = max_id

            pnl_out = run_cmd(
                ["bash", "scripts/run_trade_pnl_reconstruction.sh"],
                env=pnl_env,
            )
            pnl_stats = parse_pnl_summary(pnl_out)

        closed = int(pnl_stats.get("closed", "0") or "0")
        net = float(pnl_stats.get("net", "0") or "0")
        total_trades += closed
        total_net += net

        save_campaign_window(
            database_url=database_url,
            campaign_id=args.campaign_id,
            symbol=args.symbol,
            strategy="BR_CONSERVATIVE_BREAKOUT",
            timeframe="M5",
            window_index=window.index,
            from_ts=window.from_ts,
            to_ts=window.to_ts,
            replay_stats=replay_stats,
            pnl_stats=pnl_stats,
            min_id=min_id,
            max_id=max_id,
        )

        print(
            "BR_REPLAY_CAMPAIGN_WINDOW",
            f"index={window.index}",
            f"symbol={args.symbol}",
            f"from_ts={window.from_ts.isoformat()}",
            f"to_ts={window.to_ts.isoformat()}",
            f"signals={replay_stats.get('signals_generated', '0')}",
            f"paper_orders={replay_stats.get('paper_orders', '0')}",
            f"trades_logged={replay_stats.get('trades_logged', '0')}",
            f"min_id={min_id or 'NA'}",
            f"max_id={max_id or 'NA'}",
            f"closed={closed}",
            f"net={net:.4f}",
            f"winrate={pnl_stats.get('winrate', '0')}",
            flush=True,
        )

    print(
        "BR_REPLAY_CAMPAIGN_DONE",
        f"symbol={args.symbol}",
        f"windows={len(windows)}",
        f"closed={total_trades}",
        f"net={total_net:.4f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
