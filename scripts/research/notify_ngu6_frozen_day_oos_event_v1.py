from __future__ import annotations

import os
import sys
import urllib.parse
import urllib.request


def send_message(text: str) -> None:
    token = os.getenv("TG_TOKEN") or os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    if not token:
        raise RuntimeError("telegram_token_missing")

    if not chat_id:
        raise RuntimeError("telegram_chat_id_missing")

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=15,
    ) as response:
        if response.status != 200:
            raise RuntimeError(
                f"telegram_http_status:{response.status}"
            )


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: notify_ngu6_frozen_day_oos_event_v1.py "
            "<message-file>",
            file=sys.stderr,
        )
        return 2

    path = sys.argv[1]

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        text = handle.read().strip()

    if not text:
        raise RuntimeError("telegram_message_empty")

    send_message(text)

    print("TELEGRAM_SENT=YES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
