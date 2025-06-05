"""Interface to Yandex SpeechKit for text-to-speech conversion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp
import logging
import json
import base64

from config import CONFIG

# v3 API endpoint - much better than v1!
TTS_API_URL = "https://tts.api.cloud.yandex.net/tts/v3/utteranceSynthesis"

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class TTSRequest:
    """Parameters for a TTS synthesis request"""
    text: str
    voice: str
    role: str | None = None
    lang: str = "ru-RU"
    format: str = "oggopus"
    sample_rate_hz: int = 48000  # only matters for raw formats like lpcm
    speed: str | None = None  # "0.8", "1.0", "1.2"

    def to_payload(self) -> dict[str, Any]:
        """Build the JSON that SpeechKit expects.
        
        Note: Each hint must be its own object with a single field.
        Don't try to combine them - the API will reject it.
        """
        hints: list[dict[str, Any]] = []
        
        if self.voice:
            hints.append({"voice": self.voice})
            
        # neutral is the default, no need to send it
        if self.role and self.role.lower() != "neutral":
            hints.append({"role": self.role})
            
        if self.speed and self.speed != CONFIG.default_speed:
            hints.append({"speed": str(self.speed)})

        # Audio format specification
        output_audio_spec: dict[str, Any] = {}
        if self.format == "oggopus":
            output_audio_spec["containerAudio"] = {
                "containerAudioType": "OGG_OPUS"
            }
        elif self.format == "lpcm":
            # Raw PCM, rarely needed
            output_audio_spec["rawAudio"] = {
                "audioEncoding": "LINEAR16_PCM",
                "sampleRateHertz": self.sample_rate_hz,
            }

        payload: dict[str, Any] = {
            "text": self.text,
            "lang": self.lang,
        }
        
        if hints:
            payload["hints"] = hints
        if output_audio_spec:
            payload["outputAudioSpec"] = output_audio_spec

        logger.info("TTS v3 payload: %s", payload)
        return payload


class SpeechService:
    """Handles TTS requests to Yandex SpeechKit"""

    def __init__(self) -> None:
        # Not actually used anymore, kept for compatibility
        self._headers = {
            "Authorization": f"Api-Key {CONFIG.yandex_api_key}",
            "Content-Type": "application/json"
        }

    async def synthesize(self, text: str, voice: str | None = None, role: str | None = None, speed: str | None = None) -> bytes:
        """Convert text to speech audio.
        
        Returns raw audio bytes ready to send to Telegram.
        """
        req = TTSRequest(
            text=text,
            voice=voice or CONFIG.default_voice,
            role=role or CONFIG.default_role,
            speed=speed or CONFIG.default_speed,
            format=CONFIG.default_format,
        )
        
        headers = {"Authorization": f"Api-Key {CONFIG.yandex_api_key}"}

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(TTS_API_URL, json=req.to_payload(), timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    detail = await resp.text()
                    raise RuntimeError(f"TTS request failed: {resp.status} {detail}")

                content_type = resp.headers.get("Content-Type", "")
                
                # The API returns JSON with base64-encoded audio
                if "application/json" in content_type:
                    # Streaming response - multiple JSON objects separated by newlines
                    # This happens when using SSML or very long texts
                    audio_chunks = []
                    
                    try:
                        raw_body = await resp.text()
                        lines = raw_body.strip().split('\n')
                        
                        for line in lines:
                            if not line.strip():
                                continue
                                
                            try:
                                data_json = json.loads(line)
                                logger.debug("TTS v3 JSON response keys: %s", list(data_json.keys()))
                                
                                # API might wrap the audio chunk differently
                                audio_chunk = data_json.get("audioChunk") or data_json.get("result", {}).get("audioChunk", {})
                                b64_audio = audio_chunk.get("data")
                                
                                if b64_audio:
                                    try:
                                        audio_data = base64.b64decode(b64_audio)
                                        audio_chunks.append(audio_data)
                                    except (ValueError, base64.binascii.Error) as e:
                                        logger.error("Failed to decode base64 audio: %s", e)
                                        
                            except json.JSONDecodeError as e:
                                logger.error("Failed to decode JSON line: %s — line: %s", e, line[:100])
                                
                        if not audio_chunks:
                            logger.error("No audio chunks found in streaming response")
                            raise RuntimeError("TTS API returned no audio data in streaming response")
                            
                        # Combine all chunks into single audio file
                        return b"".join(audio_chunks)
                        
                    except Exception as e:
                        logger.error("Failed to process TTS streaming response: %s", e)
                        raise RuntimeError(f"TTS API streaming response processing failed: {e}")

                # Sometimes the API just returns raw bytes (rare)
                raw_bytes = await resp.read()
                if not raw_bytes:
                    raise RuntimeError("TTS API returned no audio data (non-JSON response)")
                return raw_bytes
