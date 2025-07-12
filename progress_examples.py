"""Examples of using progress indicators in bot operations."""

import asyncio
from telegram import Update, Message
from telegram.ext import ContextTypes
from progress_utils import (
    ProgressBarIndicator, 
    SpinnerIndicator, 
    TaskProgressManager,
    AdaptiveProgressIndicator,
    show_step_progress
)

# Example 1: Using ProgressBarIndicator for file processing
async def process_large_file_example(message: Message) -> None:
    """Example of processing a large file with progress bar"""
    
    # Create progress bar for 10 steps
    progress_msg = await message.reply_text("📊 Начинаю обработку файла...")
    progress_bar = ProgressBarIndicator(progress_msg, 10, "Обработка файла")
    
    await progress_bar.start()
    
    # Simulate file processing steps
    steps = [
        "Загрузка файла",
        "Проверка формата", 
        "Анализ содержимого",
        "Извлечение данных",
        "Форматирование текста",
        "Проверка орфографии",
        "Генерация разметки",
        "Синтез речи",
        "Кодирование аудио",
        "Сохранение результата"
    ]
    
    for i, step in enumerate(steps):
        await asyncio.sleep(1)  # Simulate processing time
        await progress_bar.update(i + 1, step)
    
    await progress_bar.complete("🎉 Файл успешно обработан!")


# Example 2: Using SpinnerIndicator for multi-phase operations
async def multi_phase_synthesis_example(message: Message) -> None:
    """Example of multi-phase TTS synthesis with different spinners"""
    
    progress_msg = await message.reply_text("🔄 Подготовка...")
    
    # Define phases with different animations
    phases = [
        {
            'text': 'Анализ текста с помощью ИИ...',
            'frames': SpinnerIndicator.SPINNER_FRAMES,
            'duration': 0.15
        },
        {
            'text': 'Формирование фонетической разметки...',
            'frames': SpinnerIndicator.DOTS_FRAMES,
            'duration': 0.12
        },
        {
            'text': 'Синтез речи (может занять время)...',
            'frames': SpinnerIndicator.CLOCK_FRAMES,
            'duration': 0.2
        }
    ]
    
    spinner = SpinnerIndicator(progress_msg, phases)
    await spinner.start()
    
    # Simulate phase transitions
    await asyncio.sleep(3)
    await spinner.next_phase()
    
    await asyncio.sleep(2)
    await spinner.next_phase()
    
    await asyncio.sleep(4)
    await spinner.stop()
    
    await progress_msg.edit_text("✅ Синтез речи завершен!")


# Example 3: Using TaskProgressManager for complex workflows
async def complex_workflow_example(message: Message) -> None:
    """Example of complex workflow with task tracking"""
    
    tasks = [
        "Получение настроек пользователя",
        "Проверка доступности API",
        "Предварительная обработка текста",
        "Применение ИИ-форматирования",
        "Отправка запроса на синтез",
        "Получение аудио-данных",
        "Постобработка аудио",
        "Сохранение в кеш"
    ]
    
    manager = await show_step_progress(message, tasks)
    
    # Simulate task execution
    for i in range(len(tasks)):
        await asyncio.sleep(0.8)  # Simulate work
        await manager.next_task()
    
    await manager.complete("🚀 Все задачи выполнены успешно!")


# Example 4: Using AdaptiveProgressIndicator
async def adaptive_progress_example(message: Message) -> None:
    """Example of adaptive progress that changes based on duration"""
    
    progress_msg = await message.reply_text("⚡ Быстрая операция...")
    indicator = AdaptiveProgressIndicator(progress_msg, "Обрабатываю запрос")
    
    await indicator.start()
    
    # Simulate a potentially long operation
    await asyncio.sleep(3)  # This will trigger the upgrade to animated indicator
    
    await indicator.update_text("Операция займет больше времени...")
    await asyncio.sleep(2)
    
    await indicator.update_text("Почти готово...")
    await asyncio.sleep(1)
    
    await indicator.stop()
    await progress_msg.edit_text("✅ Операция завершена!")


# Example 5: Enhanced TTS function with progress indicators
async def enhanced_tts_with_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced TTS function with sophisticated progress indicators"""
    
    message = update.message
    text = message.text
    
    # Determine appropriate progress indicator based on text complexity
    text_length = len(text)
    word_count = len(text.split())
    
    if text_length < 100:
        # Simple quick operation
        progress_msg = await message.reply_text("⚡ Быстрый синтез...")
        await asyncio.sleep(1)
        await progress_msg.edit_text("✅ Готово!")
        
    elif text_length < 500:
        # Medium complexity - use spinner
        await multi_phase_synthesis_example(message)
        
    elif text_length < 1000:
        # Complex text - use task manager
        await complex_workflow_example(message)
        
    else:
        # Very long text - use progress bar
        await process_large_file_example(message)


# Example 6: Real-world integration with error handling
async def robust_tts_with_progress(text: str, message: Message) -> None:
    """Real-world TTS with robust progress handling"""
    
    progress_msg = await message.reply_text("🔄 Подготовка синтеза...")
    
    try:
        # Determine the best progress indicator
        if len(text) > 200:
            # Use task progress for longer texts
            tasks = [
                "Анализ текста",
                "Генерация разметки", 
                "Синтез речи",
                "Кодирование аудио"
            ]
            
            manager = TaskProgressManager(progress_msg, tasks)
            await manager.start()
            
            # Step 1: Text analysis
            await asyncio.sleep(1)
            await manager.next_task()
            
            # Step 2: Markup generation
            await asyncio.sleep(1.5)
            await manager.next_task()
            
            # Step 3: Speech synthesis (longest step)
            await asyncio.sleep(3)
            await manager.next_task()
            
            # Step 4: Audio encoding
            await asyncio.sleep(0.5)
            await manager.complete("🎵 Аудио готово!")
            
        else:
            # Use simple animated progress for shorter texts
            from bot import ProgressIndicator, VOICE_PROGRESS_FRAMES
            
            indicator = ProgressIndicator(
                progress_msg, 
                "Синтезирую речь...",
                VOICE_PROGRESS_FRAMES
            )
            await indicator.start()
            
            # Simulate synthesis
            await asyncio.sleep(2)
            
            await indicator.stop()
            await progress_msg.edit_text("✅ Синтез завершен!")
            
    except Exception as e:
        # Handle errors gracefully
        await progress_msg.edit_text(
            f"❌ Ошибка при синтезе: {str(e)[:100]}..."
        )


# Example 7: Batch processing with progress
async def batch_tts_with_progress(messages: list, telegram_message: Message) -> None:
    """Process multiple TTS requests with progress tracking"""
    
    if not messages:
        await telegram_message.reply_text("❌ Нет сообщений для обработки")
        return
    
    progress_msg = await telegram_message.reply_text("📊 Запускаю пакетную обработку...")
    
    # Create progress bar for batch processing
    progress_bar = ProgressBarIndicator(
        progress_msg, 
        len(messages), 
        "Пакетная обработка TTS"
    )
    
    await progress_bar.start()
    
    results = []
    for i, msg in enumerate(messages):
        status = f"Обрабатываю сообщение {i + 1}: {msg[:30]}..."
        await progress_bar.update(i + 1, status)
        
        # Simulate processing
        await asyncio.sleep(0.5)
        results.append(f"processed_{i}")
    
    await progress_bar.complete(f"✅ Обработано {len(results)} сообщений!")
    
    return results


# Example 8: Context-aware progress selection
def select_progress_indicator(operation_type: str, complexity: int, message: Message):
    """Select appropriate progress indicator based on operation context"""
    
    if operation_type == "quick_tts" and complexity < 50:
        return "simple"
    elif operation_type == "ai_formatting" or complexity > 100:
        return "spinner"
    elif operation_type == "batch_processing":
        return "progress_bar"
    elif operation_type == "ssml_synthesis":
        return "task_manager"
    else:
        return "adaptive"


# Usage examples in bot commands
async def demo_progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to demonstrate different progress indicators"""
    
    if not context.args:
        await update.message.reply_text(
            "Использование: /demo_progress [тип]\n\n"
            "Доступные типы:\n"
            "• bar - прогресс-бар\n"
            "• spinner - многофазный спиннер\n"
            "• tasks - менеджер задач\n"
            "• adaptive - адаптивный прогресс\n"
            "• batch - пакетная обработка"
        )
        return
    
    progress_type = context.args[0].lower()
    
    if progress_type == "bar":
        await process_large_file_example(update.message)
    elif progress_type == "spinner":
        await multi_phase_synthesis_example(update.message)
    elif progress_type == "tasks":
        await complex_workflow_example(update.message)
    elif progress_type == "adaptive":
        await adaptive_progress_example(update.message)
    elif progress_type == "batch":
        test_messages = ["Привет", "Как дела?", "Что нового?", "До свидания"]
        await batch_tts_with_progress(test_messages, update.message)
    else:
        await update.message.reply_text("❌ Неизвестный тип прогресса")


# Integration with existing bot handlers
async def enhanced_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced text handler with intelligent progress selection"""
    
    message = update.message
    text = message.text
    
    # Analyze text to choose appropriate progress indicator
    text_length = len(text)
    has_special_chars = any(char in text for char in "<>[]{}()")
    
    if text_length < 50:
        # Quick operation - minimal progress
        await message.chat.send_action("upload_voice")
        progress_msg = await message.reply_text("⚡ Синтез...")
        await asyncio.sleep(1)
        await progress_msg.delete()
        
    elif text_length < 200 and not has_special_chars:
        # Standard operation - animated progress
        await robust_tts_with_progress(text, message)
        
    elif has_special_chars:
        # Complex markup - task-based progress
        await complex_workflow_example(message)
        
    else:
        # Long text - progress bar
        await process_large_file_example(message) 