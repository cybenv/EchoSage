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
```

## Bot commands

- `/start`   – short help
- `/help`    – detailed help
- `/set_voice`, `/set_role`, `/set_speed` – pick voice / emotion / speed
- `/settings` – show current settings
- `/reset`   – reset all settings to defaults
- `/speak_ssml` – synthesize speech with SSML markup (v1 API)
- `/toggle_format` – enable/disable AI-powered text formatting
- `/demo_markup` – see examples of TTS v3 markup

## TTS v3 Markup Support

The bot supports Yandex SpeechKit v3's native TTS markup for natural speech synthesis:

### Markup Elements:
- `sil<[ms]>` — explicit pause with duration (100-5000ms) 
- `+` — lexical stress on vowel (e.g., м+олоко)
- `<[size]>` — context-dependent pause (tiny/small/medium/large/huge)
- `**word**` — emphasis on word

### Examples:
```
Привет, sil<[300]> мир!                         # 300ms pause
Стоп! sil<[500]> Подумай об этом.              # 500ms pause after exclamation
Унылая пора! sil<[300]> Очей очарованье!       # Poetry with pauses
Зам+ок на двери и з+амок короля                # Different stress for different meanings
```

### Auto-Formatting with AI

When enabled, the bot uses YandexGPT to automatically add appropriate pauses and stress markers:

**Input:** "Мороз и солнце; день чудесный!"  
**Output:** "Мороз и солнце; sil<[200]> день чудесный!"

Toggle this feature with `/toggle_format`.

## SSML Support (Legacy)

For backward compatibility, the bot still supports SSML via the `/speak_ssml` command:

```
/speak_ssml <speak>Вот несколько примеров использования SSML. Вы можете добавить в текст паузу любой длины:<break time="2s"/> та-дааам!</speak>
```

**Note:** SSML uses the v1 API and is ~3× slower than v3 markup. Use TTS markup for better performance.

## Performance Comparison

| Feature | SSML (v1) | TTS Markup (v3) |
|---------|-----------|-----------------|
| Latency | ~1.8s | ~0.6s |
| Syntax | XML tags | Simple markers |
| AI Format | NO | YES |

## Deployment

Running on Yandex Cloud Functions? Use the `handler` entry-point inside `bot.py` and set the same environment variables.

## Docker

I like to keep my deployments flexible, so here's how I run EchoSage inside a container:

### Plain Docker

```bash
# Build it
docker build -t echosage-bot .

# Run it (loads your .env automatically)
docker run -d --env-file .env echosage-bot
```

### Docker Compose

For an even simpler setup, I just run:

```bash
# Fire it up
docker-compose up --build -d

# Check what's happening
docker-compose logs -f echosage
```

### Stopping

```bash
# Plain Docker: find container ID first
docker ps
docker stop <container_id>

# Docker Compose: just kill it
docker-compose down
```

## License

Public domain (see `LICENSE`). Enjoy!
