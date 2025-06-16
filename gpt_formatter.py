"""YandexGPT-powered text preprocessing for TTS markup generation."""
from __future__ import annotations

import re
import logging
from typing import Optional, Dict, List, Any, Union
import aiohttp
import json

from config import CONFIG

logger = logging.getLogger(__name__)

# YandexGPT API
GPT_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

class TTSPreprocessor:
    """Formats Russian text for Yandex TTS v3 using AI and rule-based processing"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the preprocessor with API credentials.
        
        Args:
            api_key: Yandex Cloud API key. If not provided, uses CONFIG.
        """
        self.api_key: str = api_key or CONFIG.yandex_api_key
        self.headers: Dict[str, str] = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Simple punctuation rules for basic processing
        self.simple_rules: Dict[str, str] = {
            r"([.!?])\s+": r"\1 sil<[300]> ",  # Add pause after sentence ending punctuation
            r";\s+": r"; sil<[200]> ",  # Pause after semicolon
            r"([,:])\s+": r"\1 ",  # Keep comma and colon spacing
            r"—\s*": r" sil<[200]> ",  # Pause for em dash
            r"\s+-\s+": r" sil<[200]> ",  # Pause for spaced hyphen
        }
        
    async def format_text(self, text: str, use_gpt: bool = True) -> str:
        """Format text for TTS markup.
        
        Args:
            text: Russian text to format
            use_gpt: Whether to use GPT for complex formatting (vs rule-based only)
            
        Returns:
            Formatted text with TTS markup
        """
        # Remove any existing markup to avoid conflicts
        text = self._clean_text(text)
        
        # Determine if text is complex enough for GPT processing
        if use_gpt and self._is_complex_text(text):
            try:
                formatted = await self._format_with_gpt(text)
                # Validate GPT output before returning
                if self._validate_markup(formatted):
                    return formatted
                else:
                    logger.warning("GPT markup validation failed, falling back to rules")
            except Exception as e:
                logger.error(f"GPT formatting error: {e}, falling back to rule-based")
        
        # Apply rule-based formatting as fallback or primary method
        return self._apply_simple_rules(text)
    
    def _clean_text(self, text: str) -> str:
        """Remove any existing TTS markup from text"""
        # Remove existing pauses
        text = re.sub(r'sil<\[\d+\]>', '', text)
        # Remove silence markers
        text = re.sub(r'sil<\[\d+\]>', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _is_complex_text(self, text: str) -> bool:
        """Determine if text requires AI processing"""
        # Complex if it has:
        # - Multiple sentences
        # - Complex punctuation patterns
        # - Long sentences (>50 words)
        # - Poetry indicators (multiple exclamation marks, specific rhythm)
        
        sentence_count = len(re.split(r'[.!?]+', text)) - 1
        has_complex_punct = bool(re.search(r'[;:—]', text))
        word_count = len(text.split())
        has_poetry_markers = bool(re.search(r'!.*!', text)) or text.count('\n') > 2
        
        return (sentence_count > 2 or 
                has_complex_punct or 
                word_count > 50 or 
                has_poetry_markers)
    
    async def _format_with_gpt(self, text: str) -> str:
        """Use YandexGPT to generate TTS markup"""
        prompt = f"""Отформатируй русский текст для синтеза речи Yandex SpeechKit v3. 
Используй следующую разметку:
1. sil<[t]> для явных пауз (t=100-5000мс)
2. Ударения в словах через + (например: м+олок+о)

Правила:
- После восклицательного знака всегда ставь sil<[300]>
- После точки с запятой используй sil<[300]>
- В сложных предложениях добавляй паузы между частями
- НЕ используй SSML теги

Входной текст: {text}

Отформатированный текст:"""

        payload: Dict[str, Any] = {
            "modelUri": f"gpt://{CONFIG.yandex_folder_id}/{CONFIG.gpt_model}",
            "completionOptions": {
                "stream": False,
                "temperature": 0.1,
                "maxTokens": len(text) * 2
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Ты — эксперт по подготовке текстов для синтеза речи с использованием технологий Yandex. Твоя задача — оптимизировать текст так, чтобы синтезированная речь звучала естественно и чётко, соответствуя интонациям живого общения и улучшая восприятие информации слушателем."
                },
                {
                    "role": "user", 
                    "text": prompt
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GPT_API_URL, 
                headers=self.headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"GPT API error {response.status}: {error_text}")
                
                result = await response.json()
                return result['result']['alternatives'][0]['message']['text'].strip()
    
    def _apply_simple_rules(self, text: str) -> str:
        """Apply simple rule-based formatting for TTS markup.
        
        Rules:
        - Add pauses after sentences (. ! ?)
        - Add pauses after semicolons and conjunctions
        - Add pauses after commas in long clauses
        """
        formatted: str = text
        
        # Add pauses after sentence endings
        formatted = re.sub(r'([.!?])\s+', r'\1 sil<[300]> ', formatted)
        
        # Add pauses after semicolons  
        formatted = re.sub(r';\s+', r'; sil<[200]> ', formatted)
        
        # Add pauses after conjunctions with commas
        conjunction_pattern: str = r',\s+(но|а|однако|хотя|чтобы|если|когда|пока|после того как)\s+'
        formatted = re.sub(conjunction_pattern, r', sil<[200]> \1 ', formatted)
        
        # Add pauses after long introductory phrases
        intro_pattern: str = r'^(Когда|После того как|Если|Хотя|Несмотря на то что)[^,]+,\s+'
        formatted = re.sub(intro_pattern, lambda m: m.group(0).rstrip() + ' sil<[200]> ', formatted)
        
        # Clean up multiple spaces
        formatted = re.sub(r'\s+', ' ', formatted).strip()
        
        return formatted
    
    def _validate_markup(self, text: str) -> bool:
        """Validate that markup is correctly formatted"""
        try:
            # First, remove valid TTS markup to check for SSML
            temp_text: str = re.sub(r'sil<\[\d+\]>', '', text)
            
            # Check for invalid SSML tags (not applicable for v3)
            if re.search(r'<[^>]+>', temp_text):
                return False
            
            # Check silence markers are properly formatted
            silence_pattern: str = r'sil<\[(\d+)\]>'  
            for match in re.finditer(silence_pattern, text):
                duration: int = int(match.group(1))
                if duration < 100 or duration > 5000:
                    return False
            
            # Check that sil<[t]> markers don't appear in invalid positions
            if re.search(r'sil<\[\d+\]>\s*sil<\[\d+\]>', text) or re.search(r'^sil<\[\d+\]>', text):
                return False
            
            return True
        except Exception:
            return False


# Convenience function for direct use
async def format_for_tts(text: str, use_gpt: bool = True) -> str:
    """Format text for TTS synthesis.
    
    Args:
        text: Russian text to format
        use_gpt: Whether to use AI formatting for complex texts
        
    Returns:
        Formatted text with TTS markup
    """
    preprocessor = TTSPreprocessor()
    return await preprocessor.format_text(text, use_gpt)
