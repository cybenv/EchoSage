"""Russian text-to-speech Telegram bot powered by Yandex SpeechKit.

Simple bot that takes Russian text messages and converts them to voice messages.
Built for personal use but feel free to adapt it for your needs.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Final, Any, Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
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
VOICE_NAMES_RU: Dict[str, str] = {
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
}

ROLE_NAMES_RU: Dict[str, str] = {
    "neutral": "Покой",
    "good": "Добро",
    "evil": "Злоба",
    "friendly": "Дружба",
    "strict": "Строгий",
    "whisper": "Шёпот",
}

SPEED_NAMES_RU: Dict[str, str] = {
    "0.8": "Медленная",
    "1.0": "Обычная",
    "1.6": "Быстрая",
}

# Used for inline messages when settings change
SETTING_NAMES_RU: Dict[str, str] = {
    "voice": "голос",
    "role": "эмоцию",
    "speed": "скорость",
}

# Progress animation frames
PROGRESS_FRAMES = [
    "🔄",
    "⏳",
    "🔄",
    "⏳",
    "🔄"
]

VOICE_PROGRESS_FRAMES = [
    "🎤",
    "🎵",
    "🔊",
    "🎶",
    "🎧"
]

speech_service: Final[SpeechService] = SpeechService()

WELCOME = (
    "Привет, Лен! Отправь мне текст на русском, и я пришлю ответ в виде голосового сообщения.\n\n"
    "⚙️ <b>Настройки:</b> /settings — удобное меню для настройки голоса, эмоций и скорости\n\n"
    "Другие команды:\n"
    "- /help — подробная помощь и примеры\n"
    "- /speak_ssml — синтез речи с SSML-разметкой\n"
    "- /demo_markup — примеры TTS разметки"
)

HELP = (
    "<b>Как мною пользоваться</b>\n\n"
    "1. Просто пришли мне сообщение на русском.\n"
    "2. Я преобразую текст в речь и пришлю его в виде голосового сообщения.\n\n"
    "<b>⚙️ Настройки</b>\n\n"
    "Используй команду <b>/settings</b> для открытия интерактивного меню настроек.\n"
    "В меню ты можешь:\n"
    "• Выбрать голос и эмоцию\n"
    "• Изменить скорость речи\n"
    "• Включить/выключить автоформатирование\n"
    "• Сбросить настройки по умолчанию\n\n"
    f"Голос по умолчанию: <code>{VOICE_NAMES_RU.get(CONFIG.default_voice, CONFIG.default_voice)}</code>\n"
    f"Эмоция по умолчанию: <code>{ROLE_NAMES_RU.get(CONFIG.default_role, CONFIG.default_role) if CONFIG.default_role else '—'}</code>\n"
    f"Скорость по умолчанию: <code>{SPEED_NAMES_RU.get(CONFIG.default_speed, CONFIG.default_speed)}</code>\n\n"
    "Поддерживаются только русскоязычные сообщения.\n\n"
    "<b>SSML-разметка</b>\n"
    "Используй команду /speak_ssml для синтеза с разметкой SSML.\n"
    "Пример: <code>/speak_ssml &lt;speak&gt;Привет, &lt;break time=\"500ms\"/&gt; мир!&lt;/speak&gt;</code>\n\n"
    "Дополнительные команды:\n"
    "/settings, /speak_ssml, /demo_markup"
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
]

# Not all voices support all emotions - this maps what's actually available
# If a voice isn't here, it only supports "neutral"
VOICE_ROLE_MAP: Dict[str, List[str]] = {
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
}

ROLES = [
    "neutral",
    "good",
    "evil",
    "friendly",
    "strict",
    "whisper",
]

SPEEDS = ["0.8", "1.0", "1.6"]


class ProgressIndicator:
    """Animated progress indicator for long-running operations"""
    
    def __init__(self, message: Message, text: str, frames: List[str] = None):
        self.message = message
        self.base_text = text
        self.frames = frames or PROGRESS_FRAMES
        self.current_frame = 0
        self.is_running = False
        self._task = None
    
    async def start(self) -> None:
        """Start the progress animation"""
        self.is_running = True
        self._task = asyncio.create_task(self._animate())
    
    async def stop(self) -> None:
        """Stop the progress animation"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _animate(self) -> None:
        """Animate the progress indicator"""
        try:
            while self.is_running:
                frame = self.frames[self.current_frame]
                try:
                    await self.message.edit_text(f"{frame} {self.base_text}")
                except Exception as e:
                    # Ignore edit errors (message might be deleted or rate-limited)
                    logger.debug(f"Progress animation edit error: {e}")
                
                self.current_frame = (self.current_frame + 1) % len(self.frames)
                await asyncio.sleep(0.8)  # Change frame every 800ms
                
        except asyncio.CancelledError:
            pass
    
    async def update_text(self, new_text: str) -> None:
        """Update the progress text"""
        self.base_text = new_text
        frame = self.frames[self.current_frame]
        try:
            await self.message.edit_text(f"{frame} {new_text}")
        except Exception as e:
            logger.debug(f"Progress text update error: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message"""
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.HTML)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed help"""
    await update.message.reply_text(HELP, parse_mode=ParseMode.HTML)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert text messages to speech with animated progress indicators"""
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
    
    # Initial typing indicator
    await message.chat.send_action("typing")
    
    # Show initial progress message
    progress_msg = await message.reply_text("🔄 Обрабатываю текст...")
    
    try:
        # Saved preferences
        user_settings = UserSettings(update.effective_user.id)
        settings = user_settings.load()
        
        # Determine if we need formatting (longer operations)
        text_length = len(text)
        needs_formatting = settings.get("auto_format", CONFIG.enable_auto_format)
        
        # Start progress animation
        if text_length > 100 or needs_formatting:
            # For longer texts or formatting, show animated progress
            progress_indicator = ProgressIndicator(
                progress_msg, 
                "Анализирую текст для естественного звучания...", 
                PROGRESS_FRAMES
            )
            await progress_indicator.start()
        else:
            # For short texts, just update once
            await progress_msg.edit_text("🔄 Готовлю синтез речи...")
        
        # Send voice upload action
        await message.chat.send_action("upload_voice")
        
        # Update progress for synthesis phase
        if text_length > 100 or needs_formatting:
            await progress_indicator.update_text("Синтезирую речь...")
            # Change to voice frames
            progress_indicator.frames = VOICE_PROGRESS_FRAMES
            progress_indicator.current_frame = 0
        else:
            await progress_msg.edit_text("🎤 Синтезирую речь...")
        
        # Perform TTS synthesis
        audio_bytes = await speech_service.synthesize(
            text=text,
            voice=settings.get("voice"),
            role=settings.get("role"),
            speed=settings.get("speed"),
            auto_format=settings.get("auto_format"),
            use_markup=settings.get("use_markup"),
        )
        
        # Stop progress animation
        if text_length > 100 or needs_formatting:
            await progress_indicator.stop()
        
        # Delete progress message and send voice
        await progress_msg.delete()
        await message.reply_voice(audio_bytes)
        
    except Exception as exc:
        # Stop progress animation if running
        if 'progress_indicator' in locals():
            await progress_indicator.stop()
        
        logger.exception("TTS failed")
        error_msg = str(exc)
        
        # Specific error handling with progress message update
        if "Too long text" in error_msg:
            await progress_msg.edit_text(
                "❌ <b>Текст слишком длинный</b>\n\n"
                "Попробуй разделить сообщение на несколько частей.\n"
                "Максимальная длина: ~5000 символов",
                parse_mode=ParseMode.HTML
            )
        elif "400" in error_msg and settings.get("auto_format", CONFIG.enable_auto_format):
            # Try again without formatting if it was a formatting error
            logger.info("Retrying without formatting due to 400 error")
            await progress_msg.edit_text("⚠️ Повторяю без форматирования...")
            
            try:
                await message.chat.send_action("upload_voice")
                audio_bytes = await speech_service.synthesize(
                    text=text,
                    voice=settings.get("voice"),
                    role=settings.get("role"),
                    speed=settings.get("speed"),
                    auto_format=False,  # Disable formatting
                    use_markup=False,   # Also disable markup to be safe
                )
                await progress_msg.delete()
                await message.reply_voice(audio_bytes)
                await message.reply_text(
                    "✅ Аудио создано без автоматического форматирования.\n"
                    "Чтобы отключить форматирование насовсем, используй /toggle_format",
                    parse_mode=ParseMode.HTML
                )
            except Exception as retry_exc:
                logger.exception("Retry without formatting also failed")
                await progress_msg.edit_text(
                    "❌ <b>Ошибка синтеза речи</b>\n\n"
                    "Не удалось создать аудио даже без форматирования.\n"
                    "Попробуй упростить текст или обратись позже.",
                    parse_mode=ParseMode.HTML
                )
        elif "UNAUTHORIZED" in error_msg or "401" in error_msg:
            await progress_msg.edit_text(
                "🔐 <b>Ошибка авторизации</b>\n\n"
                "Проблема с API ключом. Обратись к администратору бота.",
                parse_mode=ParseMode.HTML
            )
        elif "timeout" in error_msg.lower():
            await progress_msg.edit_text(
                "⏱ <b>Превышено время ожидания</b>\n\n"
                "Сервер не успел обработать запрос. Попробуй ещё раз.",
                parse_mode=ParseMode.HTML
            )
        elif "SSML not supported in v3" in error_msg:
            await progress_msg.edit_text(
                "📝 <b>Обнаружена SSML-разметка</b>\n\n"
                "Для синтеза с SSML используй команду:\n"
                "<code>/speak_ssml &lt;speak&gt;твой текст&lt;/speak&gt;</code>",
                parse_mode=ParseMode.HTML
            )
        else:
            # Generic error but with more context
            await progress_msg.edit_text(
                "❌ <b>Ошибка при синтезе речи</b>\n\n"
                f"Детали: <code>{error_msg[:200]}</code>\n\n"
                "Попробуй:\n"
                "• Упростить текст\n"
                "• Отключить форматирование: /toggle_format\n"
                "• Повторить попытку позже",
                parse_mode=ParseMode.HTML
            )


async def speak_ssml(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle SSML synthesis command with progress indicators"""
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
    
    # Initial typing indicator
    await message.chat.send_action("typing")
    
    # Show progress message for SSML (always show since SSML is more complex)
    progress_msg = await message.reply_text("🔄 Обрабатываю SSML-разметку...")
    
    # Start progress animation
    progress_indicator = ProgressIndicator(
        progress_msg, 
        "Парсю SSML-разметку...", 
        PROGRESS_FRAMES
    )
    await progress_indicator.start()
    
    try:
        # Saved preferences
        user_settings = UserSettings(update.effective_user.id)
        settings = user_settings.load()
        
        # Update progress for synthesis phase
        await message.chat.send_action("upload_voice")
        await progress_indicator.update_text("Синтезирую SSML в речь...")
        progress_indicator.frames = VOICE_PROGRESS_FRAMES
        progress_indicator.current_frame = 0
        
        # Perform SSML synthesis
        audio_bytes = await speech_service.synthesize(
            ssml=ssml_text,
            voice=settings.get("voice"),
            role=settings.get("role"),
            speed=settings.get("speed"),
        )
        
        # Stop progress animation
        await progress_indicator.stop()
        
        # Delete progress message and send voice
        await progress_msg.delete()
        await message.reply_voice(audio_bytes)
        
    except Exception as exc:
        # Stop progress animation
        await progress_indicator.stop()
        
        logger.exception("SSML TTS failed")
        error_msg = str(exc)
        
        if "YANDEX_FOLDER_ID" in error_msg:
            await progress_msg.edit_text(
                "🔧 <b>Требуется настройка</b>\n\n"
                "Для использования SSML необходимо указать YANDEX_FOLDER_ID в файле .env\n"
                "Получить folder_id можно в консоли Yandex Cloud.",
                parse_mode=ParseMode.HTML
            )
        elif "400" in error_msg:
            await progress_msg.edit_text(
                "❌ <b>Ошибка в SSML-разметке</b>\n\n"
                "Проверь правильность синтаксиса. Возможные причины:\n"
                "• Незакрытые теги\n"
                "• Неверные атрибуты\n"
                "• Недопустимые элементы\n\n"
                "📚 Документация: https://yandex.cloud/ru/docs/speechkit/tts/ssml",
                parse_mode=ParseMode.HTML
            )
        elif "UNAUTHORIZED" in error_msg or "401" in error_msg:
            await progress_msg.edit_text(
                "🔐 <b>Ошибка авторизации</b>\n\n"
                "Проблема с API ключом или folder_id. Обратись к администратору бота.",
                parse_mode=ParseMode.HTML
            )
        elif "timeout" in error_msg.lower():
            await progress_msg.edit_text(
                "⏱ <b>Превышено время ожидания</b>\n\n"
                "Сервер не успел обработать запрос. Попробуй упростить SSML или повтори позже.",
                parse_mode=ParseMode.HTML
            )
        elif "Too long" in error_msg:
            await progress_msg.edit_text(
                "📝 <b>SSML слишком длинный</b>\n\n"
                "Попробуй сократить текст или разделить на части.",
                parse_mode=ParseMode.HTML
            )
        else:
            await progress_msg.edit_text(
                "❌ <b>Ошибка при синтезе SSML</b>\n\n"
                f"Детали: <code>{error_msg[:200]}</code>\n\n"
                "Проверь корректность разметки и попробуй ещё раз.",
                parse_mode=ParseMode.HTML
            )


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


def _build_settings_menu(user_id: int) -> InlineKeyboardMarkup:
    """Build the main settings menu with current values"""
    user_settings = UserSettings(user_id)
    settings = user_settings.load()
    
    voice = settings.get("voice", CONFIG.default_voice)
    role = settings.get("role", CONFIG.default_role)
    speed = settings.get("speed", CONFIG.default_speed)
    auto_format = settings.get("auto_format", CONFIG.enable_auto_format)
    
    # Russian names for display
    voice_ru = VOICE_NAMES_RU.get(voice, voice)
    role_ru = ROLE_NAMES_RU.get(role, role) if role else "—"
    speed_ru = SPEED_NAMES_RU.get(speed, speed)
    format_status = "✅ Вкл" if auto_format else "❌ Выкл"
    
    # Build menu text
    menu_text = (
        "<b>⚙️ Настройки бота</b>\n\n"
        f"🎤 <b>Голос:</b> {voice_ru}\n"
        f"🎭 <b>Эмоция:</b> {role_ru}\n"
        f"⚡ <b>Скорость:</b> {speed_ru}\n"
        f"🤖 <b>Автоформатирование:</b> {format_status}\n"
    )
    
    # Create buttons
    buttons = [
        [InlineKeyboardButton("🎤 Сменить голос", callback_data="menu:voice")],
        [InlineKeyboardButton("🎭 Сменить эмоцию", callback_data="menu:role")],
        [InlineKeyboardButton("⚡ Сменить скорость", callback_data="menu:speed")],
        [InlineKeyboardButton(f"🤖 Автоформатирование: {format_status}", callback_data="menu:toggle_format")],
        [InlineKeyboardButton("🔄 Сбросить по умолчанию", callback_data="menu:reset")],
    ]
    
    return InlineKeyboardMarkup(buttons), menu_text


def _build_keyboard_with_back(options: list[str], prefix: str, back_data: str = "menu:main") -> InlineKeyboardMarkup:
    """Build keyboard with Russian labels and back button"""
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
    
    # Add back button
    rows.append([InlineKeyboardButton("⬅️ Назад в меню", callback_data=back_data)])
    
    return InlineKeyboardMarkup(rows)


async def set_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Let user pick a voice"""
    await update.message.reply_text("Выбери голос:", reply_markup=_build_keyboard(VOICES, "voice"))


async def set_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available emotions for current voice"""
    user_settings = UserSettings(update.effective_user.id)
    current_voice = user_settings.get("voice", CONFIG.default_voice)
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


async def demo_progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to demonstrate different progress indicators"""
    
    if not context.args:
        await update.message.reply_text(
            "<b>🎯 Демонстрация индикаторов прогресса</b>\n\n"
            "Используй: <code>/demo_progress [тип]</code>\n\n"
            "<b>Доступные типы:</b>\n"
            "• <code>simple</code> - простой прогресс\n"
            "• <code>animated</code> - анимированный прогресс\n"
            "• <code>bar</code> - прогресс-бар с процентами\n"
            "• <code>spinner</code> - многофазный спиннер\n"
            "• <code>tasks</code> - менеджер задач\n"
            "• <code>adaptive</code> - адаптивный прогресс\n"
            "• <code>batch</code> - пакетная обработка\n\n"
            "<b>Примеры:</b>\n"
            "<code>/demo_progress bar</code>\n"
            "<code>/demo_progress spinner</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    progress_type = context.args[0].lower()
    
    if progress_type == "simple":
        await _demo_simple_progress(update.message)
    elif progress_type == "animated":
        await _demo_animated_progress(update.message)
    elif progress_type == "bar":
        await _demo_progress_bar(update.message)
    elif progress_type == "spinner":
        await _demo_spinner_progress(update.message)
    elif progress_type == "tasks":
        await _demo_task_progress(update.message)
    elif progress_type == "adaptive":
        await _demo_adaptive_progress(update.message)
    elif progress_type == "batch":
        await _demo_batch_progress(update.message)
    else:
        await update.message.reply_text(
            f"❌ Неизвестный тип прогресса: <code>{progress_type}</code>\n\n"
            "Используй <code>/demo_progress</code> без параметров для списка доступных типов.",
            parse_mode=ParseMode.HTML
        )


async def _demo_simple_progress(message) -> None:
    """Demo simple progress indicator"""
    progress_msg = await message.reply_text("⚡ Быстрая операция...")
    await asyncio.sleep(1)
    await progress_msg.edit_text("🔄 Обработка...")
    await asyncio.sleep(1)
    await progress_msg.edit_text("✅ Готово!")


async def _demo_animated_progress(message) -> None:
    """Demo animated progress indicator"""
    progress_msg = await message.reply_text("🔄 Анимированный прогресс...")
    
    indicator = ProgressIndicator(
        progress_msg, 
        "Демонстрация анимации...",
        PROGRESS_FRAMES
    )
    await indicator.start()
    
    await asyncio.sleep(3)
    await indicator.update_text("Меняю тип анимации...")
    indicator.frames = VOICE_PROGRESS_FRAMES
    indicator.current_frame = 0
    
    await asyncio.sleep(2)
    await indicator.stop()
    await progress_msg.edit_text("✅ Анимация завершена!")


async def _demo_progress_bar(message) -> None:
    """Demo progress bar with percentage"""
    from progress_utils import ProgressBarIndicator
    
    progress_msg = await message.reply_text("📊 Подготовка прогресс-бара...")
    progress_bar = ProgressBarIndicator(progress_msg, 10, "Демо прогресс-бар")
    
    await progress_bar.start()
    
    steps = [
        "Инициализация",
        "Загрузка данных", 
        "Проверка целостности",
        "Анализ содержимого",
        "Обработка",
        "Форматирование",
        "Валидация",
        "Оптимизация",
        "Финализация",
        "Завершение"
    ]
    
    for i, step in enumerate(steps):
        await asyncio.sleep(0.5)
        await progress_bar.update(i + 1, step)
    
    await progress_bar.complete("🎉 Прогресс-бар завершен!")


async def _demo_spinner_progress(message) -> None:
    """Demo multi-phase spinner"""
    from progress_utils import SpinnerIndicator
    
    progress_msg = await message.reply_text("🌀 Подготовка многофазного спиннера...")
    
    phases = [
        {
            'text': 'Фаза 1: Быстрая обработка',
            'frames': SpinnerIndicator.SPINNER_FRAMES,
            'duration': 0.1
        },
        {
            'text': 'Фаза 2: Анализ данных',
            'frames': SpinnerIndicator.DOTS_FRAMES,
            'duration': 0.15
        },
        {
            'text': 'Фаза 3: Финальная обработка',
            'frames': SpinnerIndicator.CLOCK_FRAMES,
            'duration': 0.2
        }
    ]
    
    spinner = SpinnerIndicator(progress_msg, phases)
    await spinner.start()
    
    await asyncio.sleep(2)
    await spinner.next_phase()
    
    await asyncio.sleep(2)
    await spinner.next_phase()
    
    await asyncio.sleep(2)
    await spinner.stop()
    
    await progress_msg.edit_text("✅ Многофазный спиннер завершен!")


async def _demo_task_progress(message) -> None:
    """Demo task progress manager"""
    from progress_utils import TaskProgressManager
    
    tasks = [
        "Получение конфигурации",
        "Проверка доступности API",
        "Аутентификация",
        "Загрузка данных",
        "Обработка контента",
        "Применение фильтров",
        "Сохранение результатов"
    ]
    
    progress_msg = await message.reply_text("📋 Подготовка менеджера задач...")
    manager = TaskProgressManager(progress_msg, tasks)
    
    await manager.start()
    
    for i in range(len(tasks)):
        await asyncio.sleep(0.7)
        await manager.next_task()
    
    await manager.complete("🚀 Все задачи выполнены!")


async def _demo_adaptive_progress(message) -> None:
    """Demo adaptive progress indicator"""
    from progress_utils import AdaptiveProgressIndicator
    
    progress_msg = await message.reply_text("🤖 Запуск адаптивного прогресса...")
    indicator = AdaptiveProgressIndicator(progress_msg, "Адаптивная обработка")
    
    await indicator.start()
    
    await asyncio.sleep(3)  # This will trigger upgrade to animated
    await indicator.update_text("Операция оказалась сложнее...")
    
    await asyncio.sleep(2)
    await indicator.update_text("Почти готово...")
    
    await asyncio.sleep(1)
    await indicator.stop()
    
    await progress_msg.edit_text("✅ Адаптивный прогресс завершен!")


async def _demo_batch_progress(message) -> None:
    """Demo batch processing with progress"""
    from progress_utils import ProgressBarIndicator
    
    test_messages = [
        "Привет, как дела?",
        "Что нового?",
        "Расскажи анекдот",
        "Какая сегодня погода?",
        "До свидания!"
    ]
    
    progress_msg = await message.reply_text("📦 Запуск пакетной обработки...")
    progress_bar = ProgressBarIndicator(
        progress_msg, 
        len(test_messages), 
        "Пакетная обработка"
    )
    
    await progress_bar.start()
    
    for i, msg in enumerate(test_messages):
        status = f"Обрабатываю: {msg[:20]}..."
        await progress_bar.update(i + 1, status)
        await asyncio.sleep(0.8)
    
    await progress_bar.complete(f"📦 Обработано {len(test_messages)} сообщений!")


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show interactive settings menu"""
    user_id = update.effective_user.id
    keyboard, menu_text = _build_settings_menu(user_id)
    
    await update.message.reply_text(
        menu_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


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
    
    # Handle main menu navigation
    if key == "menu":
        if value == "main":
            # Return to main settings menu
            user_id = update.effective_user.id
            keyboard, menu_text = _build_settings_menu(user_id)
            await query.edit_message_text(menu_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            return
        elif value == "voice":
            # Show voice selection
            await query.edit_message_text(
                "🎤 <b>Выберите голос:</b>",
                reply_markup=_build_keyboard_with_back(VOICES, "voice"),
                parse_mode=ParseMode.HTML
            )
            return
        elif value == "role":
            # Show role selection for current voice
            user_settings = UserSettings(update.effective_user.id)
            current_voice = user_settings.get("voice", CONFIG.default_voice)
            available_roles = VOICE_ROLE_MAP.get(current_voice, ["neutral"])
            if not available_roles:
                available_roles = ["neutral"]
            
            voice_ru = VOICE_NAMES_RU.get(current_voice, current_voice)
            await query.edit_message_text(
                f"🎭 <b>Выберите эмоцию для голоса {voice_ru}:</b>",
                reply_markup=_build_keyboard_with_back(available_roles, "role"),
                parse_mode=ParseMode.HTML
            )
            return
        elif value == "speed":
            # Show speed selection
            await query.edit_message_text(
                "⚡ <b>Выберите скорость речи:</b>",
                reply_markup=_build_keyboard_with_back(SPEEDS, "speed"),
                parse_mode=ParseMode.HTML
            )
            return
        elif value == "toggle_format":
            # Toggle auto-formatting
            user_settings = UserSettings(update.effective_user.id)
            settings = user_settings.load()
            current = settings.get("auto_format", CONFIG.enable_auto_format)
            new_state = not current
            user_settings.update("auto_format", new_state)
            
            # Return to updated menu
            keyboard, menu_text = _build_settings_menu(update.effective_user.id)
            await query.edit_message_text(menu_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            return
        elif value == "reset":
            # Reset all settings
            user_settings = UserSettings(update.effective_user.id)
            if user_settings.reset_to_defaults():
                # Show confirmation and return to updated menu
                keyboard, menu_text = _build_settings_menu(update.effective_user.id)
                await query.edit_message_text(
                    "✅ <b>Настройки сброшены!</b>\n\n" + menu_text,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.HTML
                )
            else:
                await query.edit_message_text("❌ Ошибка при сбросе настроек. Попробуйте позже.")
            return
    
    # Handle setting changes
    if key in {"voice", "role", "speed"}:
        # Save to persistent storage
        user_settings = UserSettings(update.effective_user.id)
        user_settings.update(key, value)
        
        # Get Russian name for confirmation message
        if key == "voice":
            display_value = VOICE_NAMES_RU.get(value, value)
        elif key == "role":
            display_value = ROLE_NAMES_RU.get(value, value)
        elif key == "speed":
            display_value = SPEED_NAMES_RU.get(value, value)
        else:
            display_value = value
            
        # When voice changes, reset role and ask for new role
        if key == "voice":
            # Reset role to default to avoid incompatible combinations
            user_settings.update("role", CONFIG.default_role)

            compatible_roles = VOICE_ROLE_MAP.get(value, ["neutral"])

            # Make sure default role is compatible
            current_role = user_settings.get("role", CONFIG.default_role)
            if current_role not in compatible_roles:
                user_settings.update("role", compatible_roles[0])

            # Show role selection for new voice
            voice_ru = VOICE_NAMES_RU.get(value, value)
            await query.edit_message_text(
                f"✅ Голос изменен на: <b>{display_value}</b>\n\n"
                f"🎭 <b>Выберите эмоцию для голоса {voice_ru}:</b>",
                reply_markup=_build_keyboard_with_back(compatible_roles, "role"),
                parse_mode=ParseMode.HTML
            )
        else:
            # Return to main menu with confirmation
            keyboard, menu_text = _build_settings_menu(update.effective_user.id)
            setting_name_ru = SETTING_NAMES_RU.get(key, key)
            
            await query.edit_message_text(
                f"✅ <b>{setting_name_ru.capitalize()} изменен{'а' if key == 'speed' else ''} на: {display_value}</b>\n\n" + menu_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
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
    application.add_handler(CommandHandler("demo_progress", demo_progress_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))

    logger.info("Bot polling started")
    application.run_polling(allowed_updates=["message", "callback_query"])


# Entry point for Yandex Cloud Functions
async def handler(event: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
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
        application.add_handler(CommandHandler("demo_progress", demo_progress_command))
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
