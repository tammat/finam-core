#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import timezone, timedelta

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SYMBOL = os.getenv("GOLD_SYMBOL", "GDM6@RTSX")
TIMEFRAME = os.getenv("GOLD_TIMEFRAME", "M5")
EXIT_BARS = int(os.getenv("GOLD_EXIT_BARS", "10"))
HOURS = {int(x) for x in os.getenv("GOLD_HOURS_MSK", "15,16,17,18").split(",") if x.strip()}
LIMIT_BARS = int(os.getenv("GOLD_SHADOW_LIMIT_BARS", "500"))

MSK = timezone(timedelta(hours=3))

DDL = """
CREATE TABLE IF NOT EXISTS runtime_shadow_gold_signals (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    timeframe text NOT NULL,
    signal_ts timestamptz NOT NULL,
    side text NOT NULL,
    entry_price numeric,
    reason text,
    strategy text,
    shadow_only boolean NOT NULL DEFAULT true,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_shadow_gold_signals_symbol_ts
ON runtime_shadow_gold_signals(symbol, signal_ts);

CREATE UNIQUE INDEX IF NOT EXISTS uq_runtime_shadow_gold_signals_dedup_v1
ON runtime_shadow_gold_signals(symbol, timeframe, signal_ts, strategy);
"""

SQL = """
SELECT ts, close
FROM market_bars
WHERE symbol = %s
  AND timeframe = %s
ORDER BY ts DESC
LIMIT %s;
"""

INSERT = """
INSERT INTO runtime_shadow_gold_signals (
    symbol,
    timeframe,
    signal_ts,
    side,
    entry_price,
    reason,
    strategy,
    shadow_only,
    raw_json
)
VALUES (
    %(symbol)s,
    %(timeframe)s,
    %(signal_ts)s,
    %(side)s,
    %(entry_price)s,
    %(reason)s,
    %(strategy)s,
    true,
    %(raw_json)s
)
ON CONFLICT (symbol, timeframe, signal_ts, strategy) DO NOTHING;
"""

def main() -> None:
    print("=== RUNTIME SHADOW VALIDATION GOLD V1 ===")
    print("mode=shadow_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print("direction=SHORT_ONLY")
    print(f"hours_msk={','.join(str(x) for x in sorted(HOURS))}")
    print(f"exit_bars={EXIT_BARS}")
    print(f"limit_bars={LIMIT_BARS}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (SYMBOL, TIMEFRAME, LIMIT_BARS))
            rows = list(reversed([dict(r) for r in cur.fetchall()]))

            closes = [float(r["close"]) for r in rows if r["close"] is not None]
            timestamps = [r["ts"] for r in rows if r["close"] is not None]

            signals = []
            for i in range(20, len(closes)):
                ts = timestamps[i]
                hour_msk = ts.astimezone(MSK).hour

                if hour_msk not in HOURS:
                    continue

                mean20 = sum(closes[i - 20:i]) / 20.0
                entry = closes[i]

                # Русский комментарий: только теневая проверка утверждённого GOLD SHORT ONLY кандидата.
                if entry < mean20 * 0.998:
                    payload = {
                        "symbol": SYMBOL,
                        "timeframe": TIMEFRAME,
                        "signal_ts": ts.isoformat(),
                        "side": "SELL",
                        "entry_price": entry,
                        "mean20": mean20,
                        "hours_msk": sorted(HOURS),
                        "exit_bars": EXIT_BARS,
                        "strategy": "gold_short_only_shadow_v1",
                        "reason": "gold_short_only_runtime_shadow_candidate",
                        "shadow_only": True,
                    }
                    signals.append(payload)

            written = 0
            print("SHADOW_ROWS")

            for s in signals:
                cur.execute(
                    INSERT,
                    {
                        "symbol": SYMBOL,
                        "timeframe": TIMEFRAME,
                        "signal_ts": s["signal_ts"],
                        "side": s["side"],
                        "entry_price": s["entry_price"],
                        "reason": s["reason"],
                        "strategy": s["strategy"],
                        "raw_json": json.dumps(s, ensure_ascii=False),
                    },
                )
                if cur.rowcount == 1:
                    written += 1

                print(
                    "SHADOW_ROW "
                    f"symbol={SYMBOL} "
                    f"timeframe={TIMEFRAME} "
                    f"signal_ts={s['signal_ts']} "
                    f"side={s['side']} "
                    f"entry_price={s['entry_price']} "
                    f"reason={s['reason']} "
                    "shadow_only=1"
                )

            conn.commit()

    print()
    print(f"SIGNALS_FOUND={len(signals)}")
    print(f"SHADOW_ROWS_WRITTEN={written}")
    print("DEDUP=enabled")
    print("VERDICT=GOLD_RUNTIME_SHADOW_VALIDATION_RECORDED")
    print("RUNTIME_SHADOW_VALIDATION_GOLD_V1_1_DEDUP_OK")
    print("RUNTIME_SHADOW_VALIDATION_GOLD_V1_OK")

if __name__ == "__main__":
    main()
