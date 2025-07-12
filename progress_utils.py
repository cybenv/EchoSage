"""Advanced progress indicator utilities for Telegram bot."""
from __future__ import annotations

import asyncio
import time
from typing import List, Optional, Callable, Dict, Any
from telegram import Message
from telegram.constants import ParseMode
import logging

logger = logging.getLogger(__name__)


class ProgressBarIndicator:
    """Advanced progress bar with percentage and ETA"""
    
    def __init__(self, message: Message, total_steps: int, title: str = "Прогресс"):
        self.message = message
        self.total_steps = total_steps
        self.current_step = 0
        self.title = title
        self.start_time = time.time()
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the progress bar"""
        self.is_running = True
        self.start_time = time.time()
        await self._update_display()
        
    async def update(self, step: int, status: str = "") -> None:
        """Update progress to a specific step"""
        self.current_step = min(step, self.total_steps)
        await self._update_display(status)
        
    async def increment(self, status: str = "") -> None:
        """Increment progress by one step"""
        self.current_step = min(self.current_step + 1, self.total_steps)
        await self._update_display(status)
        
    async def complete(self, final_message: str = "✅ Завершено!") -> None:
        """Mark progress as complete"""
        self.is_running = False
        self.current_step = self.total_steps
        try:
            await self.message.edit_text(final_message, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.debug(f"Progress bar completion error: {e}")
            
    async def _update_display(self, status: str = "") -> None:
        """Update the progress bar display"""
        if not self.is_running:
            return
            
        # Calculate percentage
        percentage = (self.current_step / self.total_steps) * 100
        
        # Create progress bar
        bar_length = 10
        filled_length = int(bar_length * self.current_step // self.total_steps)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Calculate ETA
        elapsed_time = time.time() - self.start_time
        if self.current_step > 0:
            eta = (elapsed_time / self.current_step) * (self.total_steps - self.current_step)
            eta_text = f"ETA: {int(eta)}с"
        else:
            eta_text = "ETA: --с"
            
        # Build display text
        display_text = f"<b>{self.title}</b>\n\n"
        display_text += f"{bar} {percentage:.1f}%\n"
        display_text += f"{self.current_step}/{self.total_steps} • {eta_text}"
        
        if status:
            display_text += f"\n\n🔄 {status}"
            
        try:
            await self.message.edit_text(display_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.debug(f"Progress bar update error: {e}")


class SpinnerIndicator:
    """Multi-phase spinner with custom frames for different stages"""
    
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    DOTS_FRAMES = ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"]
    CLOCK_FRAMES = ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"]
    
    def __init__(self, message: Message, phases: List[Dict[str, Any]]):
        """
        Initialize multi-phase spinner
        
        Args:
            message: Telegram message to edit
            phases: List of phase configs with 'text', 'frames', 'duration' keys
        """
        self.message = message
        self.phases = phases
        self.current_phase = 0
        self.current_frame = 0
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the spinner animation"""
        self.is_running = True
        self.current_phase = 0
        self.current_frame = 0
        self._task = asyncio.create_task(self._animate())
        
    async def next_phase(self) -> None:
        """Move to next phase"""
        if self.current_phase < len(self.phases) - 1:
            self.current_phase += 1
            self.current_frame = 0
            
    async def stop(self) -> None:
        """Stop the spinner animation"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
    async def _animate(self) -> None:
        """Run the animation loop"""
        try:
            while self.is_running and self.current_phase < len(self.phases):
                phase = self.phases[self.current_phase]
                frames = phase.get('frames', self.SPINNER_FRAMES)
                text = phase.get('text', 'Загрузка...')
                duration = phase.get('duration', 0.1)
                
                frame = frames[self.current_frame]
                display_text = f"{frame} {text}"
                
                try:
                    await self.message.edit_text(display_text)
                except Exception as e:
                    logger.debug(f"Spinner animation error: {e}")
                    
                self.current_frame = (self.current_frame + 1) % len(frames)
                await asyncio.sleep(duration)
                
        except asyncio.CancelledError:
            pass


class TaskProgressManager:
    """Manages progress for complex multi-step tasks"""
    
    def __init__(self, message: Message, tasks: List[str]):
        self.message = message
        self.tasks = tasks
        self.current_task = 0
        self.is_running = False
        self._start_time = time.time()
        
    async def start(self) -> None:
        """Start task progress tracking"""
        self.is_running = True
        self._start_time = time.time()
        await self._update_display()
        
    async def next_task(self) -> None:
        """Move to next task"""
        if self.current_task < len(self.tasks) - 1:
            self.current_task += 1
            await self._update_display()
            
    async def complete(self, final_message: str = "✅ Все задачи выполнены!") -> None:
        """Mark all tasks as complete"""
        self.is_running = False
        try:
            await self.message.edit_text(final_message, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.debug(f"Task completion error: {e}")
            
    async def _update_display(self) -> None:
        """Update the task progress display"""
        if not self.is_running:
            return
            
        display_text = "<b>📋 Выполнение задач</b>\n\n"
        
        for i, task in enumerate(self.tasks):
            if i < self.current_task:
                status = "✅"
            elif i == self.current_task:
                status = "🔄"
            else:
                status = "⏳"
                
            display_text += f"{status} {task}\n"
            
        # Add timing info
        elapsed = time.time() - self._start_time
        display_text += f"\n⏱ Время: {elapsed:.1f}с"
        
        try:
            await self.message.edit_text(display_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.debug(f"Task display update error: {e}")


class AdaptiveProgressIndicator:
    """Automatically adapts progress style based on operation duration"""
    
    def __init__(self, message: Message, initial_text: str = "Обрабатываю..."):
        self.message = message
        self.initial_text = initial_text
        self.start_time = time.time()
        self.is_running = False
        self._current_indicator: Optional[Any] = None
        
    async def start(self) -> None:
        """Start adaptive progress indication"""
        self.is_running = True
        self.start_time = time.time()
        
        # Show initial simple text
        await self.message.edit_text(f"🔄 {self.initial_text}")
        
        # Wait a bit to see if operation completes quickly
        await asyncio.sleep(2.0)
        
        # If still running, upgrade to animated indicator
        if self.is_running:
            from bot import ProgressIndicator, PROGRESS_FRAMES
            self._current_indicator = ProgressIndicator(
                self.message, 
                "Операция выполняется дольше обычного...",
                PROGRESS_FRAMES
            )
            await self._current_indicator.start()
            
    async def update_text(self, new_text: str) -> None:
        """Update progress text"""
        if self._current_indicator:
            await self._current_indicator.update_text(new_text)
        else:
            try:
                await self.message.edit_text(f"🔄 {new_text}")
            except Exception as e:
                logger.debug(f"Adaptive progress update error: {e}")
                
    async def stop(self) -> None:
        """Stop adaptive progress indication"""
        self.is_running = False
        if self._current_indicator:
            await self._current_indicator.stop()


# Convenience functions for common use cases
async def show_simple_progress(message: Message, text: str, duration: float = 2.0):
    """Show simple progress message for short operations"""
    progress_msg = await message.reply_text(f"🔄 {text}")
    await asyncio.sleep(duration)
    return progress_msg


async def show_animated_progress(message: Message, text: str, frames: List[str] = None):
    """Show animated progress for longer operations"""
    from bot import ProgressIndicator, PROGRESS_FRAMES
    
    progress_msg = await message.reply_text(f"🔄 {text}")
    indicator = ProgressIndicator(progress_msg, text, frames or PROGRESS_FRAMES)
    await indicator.start()
    return indicator


async def show_step_progress(message: Message, steps: List[str]) -> TaskProgressManager:
    """Show step-by-step progress for complex operations"""
    progress_msg = await message.reply_text("📋 Подготовка...")
    manager = TaskProgressManager(progress_msg, steps)
    await manager.start()
    return manager 