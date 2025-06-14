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
YANDEX_FOLDER_ID=...     # required for SSML support

# Optional (defaults shown)
# DEFAULT_VOICE=alena
# DEFAULT_ROLE=neutral
# DEFAULT_SPEED=1.0
# DEFAULT_AUDIO_FORMAT=oggopus
```

## Bot commands

- `/start`   – short help
- `/help`    – detailed help
- `/set_voice`, `/set_role`, `/set_speed` – pick voice / emotion / speed
- `/settings` – show current settings
- `/reset`   – reset all settings to defaults
- `/speak_ssml` – synthesize speech with SSML markup

## SSML Support

The bot now supports SSML (Speech Synthesis Markup Language) for fine-grained control over speech synthesis. Use the `/speak_ssml` command followed by your SSML-formatted text.

Example:
```
/speak_ssml <speak>Вот несколько примеров использования SSML. Вы можете добавить в текст паузу любой длины:<break time="2s"/> та-дааам!</speak>
```

Learn more about SSML tags in the [Yandex SpeechKit documentation](https://yandex.cloud/ru/docs/speechkit/tts/api/tts-ssml).

## Deployment

Running on Yandex Cloud Functions? Use the `handler` entry-point inside `bot.py` and set the same environment variables.

## License

Public domain (see `LICENSE`). Enjoy! 