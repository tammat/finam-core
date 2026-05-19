from __future__ import annotations

import os
import psycopg2
import requests

from finam_core.runtime.capital_growth_telegram_digest import (
    CapitalGrowthTelegramDigest,
    GrowthDigestRow,
)


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("TELEGRAM DIGEST SKIP token/chat_id missing", flush=True)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    r = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": text[:4000],
        },
        timeout=20,
    )

    if r.ok:
        print("TELEGRAM DIGEST SEND OK", flush=True)
    else:
        print(
            f"TELEGRAM DIGEST SEND FAIL status={r.status_code} body={r.text[:500]}",
            flush=True,
        )


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    profile = os.getenv("CAPITAL_GROWTH_PROFILE", "growth")

    conn = psycopg2.connect(dsn)

    rows: list[GrowthDigestRow] = []

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    symbol,
                    decision,
                    coalesce((raw_json->'runtime_decision'->>'trade_quality_score')::float, 0),
                    coalesce((raw_json->'runtime_decision'->>'expected_value')::float, 0),
                    coalesce((raw_json->'runtime_decision'->>'capital_growth_risk_pct')::float, 0),
                    coalesce((raw_json->'runtime_decision'->>'recommended_qty')::float, 0),
                    coalesce((raw_json->'runtime_decision'->>'risk_reward')::float, 0),
                    coalesce(raw_json->'runtime_decision'->>'capital_growth_mode', ''),
                    coalesce(reason, '')
                from radar_candidate_analysis
                where source='watch_candidate_runtime_analyzer'
                order by created_at desc
                limit 20
            """)

            for r in cur.fetchall():
                rows.append(
                    GrowthDigestRow(
                        symbol=str(r[0]),
                        decision=str(r[1]),
                        score=float(r[2] or 0),
                        expected_value=float(r[3] or 0),
                        risk_pct=float(r[4] or 0),
                        qty=float(r[5] or 0),
                        rr=float(r[6] or 0),
                        mode=str(r[7]),
                        reason=str(r[8]),
                    )
                )

    text = CapitalGrowthTelegramDigest().build(
        profile=profile,
        rows=rows,
    )

    print(text, flush=True)

    if os.getenv("SEND_CAPITAL_GROWTH_DIGEST", "0") == "1":
        send_telegram(text)

    print(
        f"CAPITAL_GROWTH_DIGEST_OK rows={len(rows)} profile={profile}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
