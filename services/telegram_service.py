import os

import requests


TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_API_TIMEOUT = 10


def send_telegram_message(
    chat_id: int,
    text: str,
) -> bool:
    if not TELEGRAM_BOT_TOKEN:
        print(
            "Missing TELEGRAM_BOT_TOKEN"
        )
        return False

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=TELEGRAM_API_TIMEOUT,
        )

        response.raise_for_status()

        return True

    except Exception as error:
        print(
            f"Telegram send error: {error}"
        )

        return False