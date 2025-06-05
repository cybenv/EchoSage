# EchoSage

A no-frills Telegram bot that turns Russian text messages into voice with Yandex SpeechKit.

## Quick start

1.  Python 3.10+ and a Telegram bot token from **@BotFather** are required.
2.  Enable Yandex SpeechKit, grab an API key.
3.  `pip install -r requirements.txt`
4.  Copy `.env.example` ➜ `.env` and fill in your keys.
5.  `python bot.py` — the bot starts in polling mode.

## .env keys

```
TELEGRAM_BOT_TOKEN=...   # required
YANDEX_API_KEY=...       # required

# Optional (defaults shown)
# DEFAULT_VOICE=alena
# DEFAULT_ROLE=neutral
# DEFAULT_SPEED=1.0
```

## Bot commands

- `/start`   – short help
- `/help`    – detailed help
- `/set_voice`, `/set_role`, `/set_speed` – pick voice / emotion / speed
- `/settings` – show current settings

## Deployment

Running on Yandex Cloud Functions? Use the `handler` entry-point inside `bot.py` and set the same environment variables.

## License

Public domain (see `LICENSE`). Enjoy! 