"""Russian text-to-speech Telegram bot powered by Yandex SpeechKit.

Simple bot that takes Russian text messages and converts them to voice messages.
Built for personal use but feel free to adapt it for your needs.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Final

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import CONFIG
from speech_service import SpeechService
from user_settings import UserSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Russian translations UI
VOICE_NAMES_RU = {
    "alena": "Алёна",
    "alexander": "Александр",
    "anton": "Антон",
    "dasha": "Даша",
    "ermil": "Ермил",
    "filipp": "Филипп",
    "jane": "Джейн",
    "julia": "Юлия",
    "kirill": "Кирилл",
    "lera": "Лера",
    "masha": "Маша",
    "marina": "Марина",
    "omazh": "Омаж",
    "zahar": "Захар",
    "john": "Джон",
}

ROLE_NAMES_RU = {
    "neutral": "Покой",
    "good": "Добро",
    "evil": "Злоба",
    "friendly": "Дружба",
    "strict": "Строгий",
    "whisper": "Шёпот",
}

SPEED_NAMES_RU = {
    "0.8": "Медленная",
    "1.0": "Обычная",
    "1.2": "Быстрая",
}

# Used for inline messages when settings change
SETTING_NAMES_RU = {
    "voice": "голос",
    "role": "эмоцию",
    "speed": "скорость",
}

speech_service: Final[SpeechService] = SpeechService()

WELCOME = (
    "Привет, Лен! Отправь мне текст на русском, и я пришлю ответ в виде голосового сообщения.\n\n"
    "Доступные команды:\n"
    "- /start — краткая справка\n"
    "- /help — подробная помощь и примеры\n"
    "- /set_voice — выбрать голос\n"
    "- /set_role — выбрать эмоцию\n"
    "- /set_speed — выбрать скорость\n"
    "- /settings — показать текущие настройки\n"
    "- /reset — сбросить настройки по умолчанию\n"
    "- /speak_ssml — синтез речи с SSML-разметкой\n"
    "- /toggle_format — включить/выключить автоформатирование\n"
    "- /demo_markup — примеры TTS разметки"
)

HELP = (
    "<b>Как мною пользоваться</b>\n\n"
    "1. Просто пришли мне сообщение на русском.\n"
    "2. Я преобразую текст в речь и пришлю его в виде голосового сообщения.\n\n"
    "<b>Параметры синтеза</b>\n\n"
    f"Голос по умолчанию: <code>{VOICE_NAMES_RU.get(CONFIG.default_voice, CONFIG.default_voice)}</code>\n"
    f"Эмоция по умолчанию: <code>{ROLE_NAMES_RU.get(CONFIG.default_role, CONFIG.default_role) if CONFIG.default_role else '—'}</code>\n"
    f"Скорость по умолчанию: <code>{SPEED_NAMES_RU.get(CONFIG.default_speed, CONFIG.default_speed)}</code>\n\n"
    "Поддерживаются только русскоязычные сообщения.\n\n"
    "<b>SSML-разметка</b>\n"
    "Используй команду /speak_ssml для синтеза с разметкой SSML.\n"
    "Пример: <code>/speak_ssml &lt;speak&gt;Привет, &lt;break time=\"500ms\"/&gt; мир!&lt;/speak&gt;</code>\n\n"
    "Дополнительные команды:\n"
    "/set_voice, /set_role, /set_speed, /settings, /reset, /speak_ssml, /toggle_format, /demo_markup"
)

# All available voices from Yandex SpeechKit v3
# Full list: https://yandex.cloud/en/docs/speechkit/tts/voices
VOICES = [
    # Russian voices
    "alena",
    "alexander",
    "anton",
    "dasha",
    "ermil",
    "filipp",
    "jane",
    "julia",
    "kirill",
    "lera",
    "masha",
    "marina",
    "omazh",
    "zahar",
    # John speaks English. Although Russian is good too.
    "john",
]

# Not all voices support all emotions - this maps what's actually available
# If a voice isn't here, it only supports "neutral"
VOICE_ROLE_MAP: dict[str, list[str]] = {
    "alena": ["neutral", "good"],
    "alexander": ["neutral", "good"],
    "anton": ["neutral", "good"],
    "dasha": ["neutral", "good", "friendly"],
    "ermil": ["neutral", "good"],
    "filipp": ["neutral"],
    "jane": ["neutral", "good", "evil"],
    "julia": ["neutral", "strict"],
    "kirill": ["neutral", "good", "strict"],
    "lera": ["neutral", "friendly"],
    "masha": ["neutral", "good", "strict", "friendly"],
    "marina": ["neutral", "whisper", "friendly"],
    "omazh": ["neutral", "evil"],
    "zahar": ["neutral", "good"],
    "john": ["neutral"],
}

ROLES = [
    "neutral",
    "good",
    "evil",
    "friendly",
    "strict",
    "whisper",
]

SPEEDS = ["0.8", "1.0", "1.2"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message"""
    await update.message.reply_text(WELCOME)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed help"""
    await update.message.reply_text(HELP, parse_mode=ParseMode.HTML)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert text messages to speech"""
    message = update.message
    assert message

    text = message.text or ""
    if not text.strip():
        return

    # Check if user accidentally sent SSML without the command
    if text.strip().startswith("<speak>") and text.strip().endswith("</speak>"):
        await message.reply_text(
            "Похоже, ты отправила SSML-разметку. Используй команду:\n"
            "<code>/speak_ssml " + text[:50] + "...</code>",
            parse_mode=ParseMode.HTML
        )
        return

    # Checker
    if not any("а" <= ch.lower() <= "я" for ch in text):
        await message.reply_text("Пожалуйста, отправь сообщение на русском.")
        return
    
    await message.chat.send_action("upload_voice")
    
    try:
        # Saved preferences
        user_settings = UserSettings(update.effective_user.id)
        settings = user_settings.load()
        
        audio_bytes = await speech_service.synthesize(
            text=text,
            voice=settings.get("voice"),
            role=settings.get("role"),
            speed=settings.get("speed"),
            auto_format=settings.get("auto_format"),
            use_markup=settings.get("use_markup"),
        )
        await message.reply_voice(audio_bytes)
    except Exception as exc:
        logger.exception("TTS failed")
        error_msg = str(exc)
        if "Too long text" in error_msg:
            await message.reply_text(
                "Текст слишком длинный. Попробуй отправить более короткое сообщение.\n"
                "Если ты хотела использовать SSML-разметку, используй команду /speak_ssml"
            )
        else:
            await message.reply_text("Ошибка при обращении к SpeechKit API. Попробуй позже.")


async def speak_ssml(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle SSML synthesis command"""
    message = update.message
    assert message
    
    # Get the SSML content after the command
    if not context.args:
        await message.reply_text(
            "Пожалуйста, укажи SSML-разметку после команды.\n"
            "Пример: <code>/speak_ssml &lt;speak&gt;Привет, &lt;break time=\"500ms\"/&gt; мир!&lt;/speak&gt;</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    ssml_text = " ".join(context.args)
    
    # Basic validation - check if it starts with <speak> and ends with </speak>
    if not ssml_text.strip().startswith("<speak>") or not ssml_text.strip().endswith("</speak>"):
        await message.reply_text(
            "SSML-разметка должна быть обёрнута в теги &lt;speak&gt;...&lt;/speak&gt;\n"
            "Пример: <code>&lt;speak&gt;Ваш текст здесь&lt;/speak&gt;</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    await message.chat.send_action("upload_voice")
    
    try:
        # Saved preferences
        user_settings = UserSettings(update.effective_user.id)
        settings = user_settings.load()
        
        audio_bytes = await speech_service.synthesize(
            ssml=ssml_text,
            voice=settings.get("voice"),
            role=settings.get("role"),
            speed=settings.get("speed"),
        )
        await message.reply_voice(audio_bytes)
    except Exception as exc:
        logger.exception("SSML TTS failed")
        error_msg = str(exc)
        if "YANDEX_FOLDER_ID" in error_msg:
            await message.reply_text(
                "Для использования SSML необходимо указать YANDEX_FOLDER_ID в файле .env\n"
                "Получить folder_id следует в консоли Yandex Cloud."
            )
        elif "400" in error_msg:
            await message.reply_text(
                "Ошибка в SSML-разметке. Проверь правильность синтаксиса.\n"
                "Подробнее о SSML: https://yandex.cloud/ru/docs/speechkit/tts/ssml"
            )
        else:
            await message.reply_text("Ошибка при обращении к SpeechKit API. Попробуй позже.")


def _build_keyboard(options: list[str], prefix: str) -> InlineKeyboardMarkup:
    """Build keyboard with Russian labels"""
    # Map internal names to Russian for display
    if prefix == "voice":
        buttons = [InlineKeyboardButton(VOICE_NAMES_RU.get(opt, opt), callback_data=f"{prefix}:{opt}") for opt in options]
    elif prefix == "role":
        buttons = [InlineKeyboardButton(ROLE_NAMES_RU.get(opt, opt), callback_data=f"{prefix}:{opt}") for opt in options]
    elif prefix == "speed":
        buttons = [InlineKeyboardButton(SPEED_NAMES_RU.get(opt, opt), callback_data=f"{prefix}:{opt}") for opt in options]
    else:
        buttons = [InlineKeyboardButton(opt, callback_data=f"{prefix}:{opt}") for opt in options]
    
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(buttons), 3):
        rows.append(buttons[i : i + 3])
    return InlineKeyboardMarkup(rows)


async def set_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Let user pick a voice"""
    await update.message.reply_text("Выбери голос:", reply_markup=_build_keyboard(VOICES, "voice"))


async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available emotions for current voice"""
    current_voice = context.user_data.get("voice", CONFIG.default_voice)
    available_roles = VOICE_ROLE_MAP.get(current_voice, ["neutral"])
    if not available_roles:
        available_roles = ["neutral"]
    
    voice_ru = VOICE_NAMES_RU.get(current_voice, current_voice)
    
    await update.message.reply_text(
        f"Эмоция для голоса: {voice_ru}",
        reply_markup=_build_keyboard(available_roles, "role"),
    )


async def set_speed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change speech speed"""
    await update.message.reply_text("Скорость речи:", reply_markup=_build_keyboard(SPEEDS, "speed"))


async def toggle_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle auto-formatting feature"""
    user_settings = UserSettings(update.effective_user.id)
    settings = user_settings.load()
    
    # Toggle the current state
    current = settings.get("auto_format", CONFIG.enable_auto_format)
    new_state = not current
    
    user_settings.update("auto_format", new_state)
    
    status = "включено ✅" if new_state else "выключено ❌"
    await update.message.reply_text(
        f"<b>Автоформатирование {status}</b>\n\n"
        f"{'Теперь я буду автоматически добавлять паузы и ударения для естественного звучания речи.' if new_state else 'Текст будет синтезироваться без дополнительной обработки.'}",
        parse_mode=ParseMode.HTML
    )


async def demo_markup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Demonstrate TTS markup capabilities"""
    # Original examples (for TTS processing)
    orig_examples = [
        ("Без разметки", "Привет, мир! Как дела?"),
        ("С паузами", "Привет, sil<[300]> мир! sil<[500]> Как дела?"),
        ("Паузы после знаков", "Стоп! sil<[300]> Подумай об этом."),
        ("Поэзия с паузами", "Унылая пора! sil<[300]> Очей очарованье!"),
        ("Ударения в словах", "Зам+ок на двери и з+амок короля"),
    ]
    
    # Properly escape brackets in examples for Telegram's HTML parser
    demo_texts = [
        (title, text.replace("<", "&lt;").replace(">", "&gt;")) 
        for title, text in orig_examples
    ]
    
    msg = "<b>Примеры TTS разметки v3:</b>\n\n"
    
    for title, text in demo_texts:
        msg += f"<b>{title}:</b>\n<code>{text}</code>\n\n"
    
    msg += (
        "<b>Доступные элементы разметки:</b>\n"
        "• <code>sil&lt;[мс]&gt;</code> — пауза заданной длительности (100-5000мс)\n"
        "• <code>+</code> — ударение на гласной (напр: м+олоко)\n"
        "• <code>&lt;[size]&gt;</code> — контекстная пауза (tiny/small/medium/large/huge)\n\n"
        "<b>Важно:</b> Разметка работает только при включенном TTS v3.\n"
        "Текущие настройки можно проверить командой /settings\n\n"
        "Попробуй отправить текст с разметкой!"
    )
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current user settings"""
    user_settings = UserSettings(update.effective_user.id)
    settings = user_settings.load()
    
    voice = settings.get("voice", CONFIG.default_voice)
    role = settings.get("role", CONFIG.default_role)
    speed = settings.get("speed", CONFIG.default_speed)
    auto_format = settings.get("auto_format", CONFIG.enable_auto_format)
    use_markup = settings.get("use_markup", CONFIG.use_tts_markup)
    
    # Russian names for display
    voice_ru = VOICE_NAMES_RU.get(voice, voice)
    role_ru = ROLE_NAMES_RU.get(role, role) if role else "—"
    speed_ru = SPEED_NAMES_RU.get(speed, speed)
    
    msg = (
        "<b>Текущие настройки</b>\n"
        f"Голос: <code>{voice_ru}</code>\n"
        f"Эмоция: <code>{role_ru}</code>\n"
        f"Скорость: <code>{speed_ru}</code>\n"
        f"Автоформатирование: <code>{'✅ Вкл' if auto_format else '❌ Выкл'}</code>\n"
        f"TTS разметка: <code>{'✅ Вкл' if use_markup else '❌ Выкл'}</code>"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset all user settings to defaults"""
    user_settings = UserSettings(update.effective_user.id)
    if user_settings.reset_to_defaults():
        # Get default values with Russian names for display
        voice_ru = VOICE_NAMES_RU.get(CONFIG.default_voice, CONFIG.default_voice)
        role_ru = ROLE_NAMES_RU.get(CONFIG.default_role, CONFIG.default_role) if CONFIG.default_role else "—"
        speed_ru = SPEED_NAMES_RU.get(CONFIG.default_speed, CONFIG.default_speed)
        
        msg = (
            "✅ Настройки сброшены!\n\n"
            "<b>Текущие настройки</b>\n"
            f"Голос: <code>{voice_ru}</code>\n"
            f"Эмоция: <code>{role_ru}</code>\n"
            f"Скорость: <code>{speed_ru}</code>\n"
            f"Автоформатирование: <code>{'✅ Вкл' if CONFIG.enable_auto_format else '❌ Выкл'}</code>\n"
            f"TTS разметка: <code>{'✅ Вкл' if CONFIG.use_tts_markup else '❌ Выкл'}</code>"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ Ошибка при сбросе настроек. Попробуй позже.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses"""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    
    data = query.data or ""
    if ":" not in data:
        return
        
    key, value = data.split(":", 1)
    if key in {"voice", "role", "speed"}:
        # Save to persistent storage
        user_settings = UserSettings(update.effective_user.id)
        user_settings.update(key, value)
        
        # Get Russian name for confirmation message
        setting_name_ru = SETTING_NAMES_RU.get(key, key)
        
        if key == "voice":
            display_value = VOICE_NAMES_RU.get(value, value)
        elif key == "role":
            display_value = ROLE_NAMES_RU.get(value, value)
        elif key == "speed":
            display_value = SPEED_NAMES_RU.get(value, value)
        else:
            display_value = value
            
        await query.edit_message_text(f"Ты выбрала {setting_name_ru}: {display_value}")

        # When voice changes, reset role/speed and ask for new role
        if key == "voice":
            # Reset to defaults to avoid incompatible combinations
            user_settings.update_multiple({
                "role": CONFIG.default_role,
                "speed": CONFIG.default_speed
            })

            compatible_roles = VOICE_ROLE_MAP.get(value, ["neutral"])

            # Make sure default role is compatible
            current_role = user_settings.get("role", CONFIG.default_role)
            if current_role not in compatible_roles:
                user_settings.update("role", compatible_roles[0])

            # Ask for emotion selection
            voice_ru = VOICE_NAMES_RU.get(value, value)
            await query.message.reply_text(
                f"Эмоция для голоса '{voice_ru}':",
                reply_markup=_build_keyboard(compatible_roles, "role"),
            )


async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unknown commands"""
    await update.message.reply_text("Неизвестная команда. Используй /help для списка доступных команд.")


def main() -> None:
    """Run the bot in polling mode (for local development)"""
    application = Application.builder().token(CONFIG.telegram_token).build()

    # Register all handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("set_voice", set_voice))
    application.add_handler(CommandHandler("set_role", set_role))
    application.add_handler(CommandHandler("set_speed", set_speed))
    application.add_handler(CommandHandler("toggle_format", toggle_format))
    application.add_handler(CommandHandler("settings", settings_cmd))
    application.add_handler(CommandHandler("reset", reset_cmd))
    application.add_handler(CommandHandler("speak_ssml", speak_ssml))
    application.add_handler(CommandHandler("demo_markup", demo_markup))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))

    logger.info("Bot polling started")
    application.run_polling(allowed_updates=["message", "callback_query"])


# Entry point for Yandex Cloud Functions
async def handler(event, context):
    """Webhook handler for serverless deployment.
    
    This is what Yandex Cloud Functions calls when a Telegram update comes in.
    If you're not using YCF, you can ignore this function.
    """
    try:
        body = json.loads(event["body"])
        
        # Have to create the app fresh each time in serverless
        application = Application.builder().token(CONFIG.telegram_token).build()
        
        # Same handlers as polling mode
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_cmd))
        application.add_handler(CommandHandler("set_voice", set_voice))
        application.add_handler(CommandHandler("set_role", set_role))
        application.add_handler(CommandHandler("set_speed", set_speed))
        application.add_handler(CommandHandler("toggle_format", toggle_format))
        application.add_handler(CommandHandler("settings", settings_cmd))
        application.add_handler(CommandHandler("reset", reset_cmd))
        application.add_handler(CommandHandler("speak_ssml", speak_ssml))
        application.add_handler(CommandHandler("demo_markup", demo_markup))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))
        
        # Process the webhook update
        await application.initialize()
        update = Update.de_json(body, application.bot)
        await application.process_update(update)
        await application.shutdown()
        
        return {
            "statusCode": 200,
            "body": json.dumps({"ok": True})
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


if __name__ == "__main__":
    main()
