"""Interface to Yandex SpeechKit for text-to-speech conversion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import aiohttp
import logging
import json
import base64

from config import CONFIG

# v3 API endpoint - much better than v1!
TTS_API_URL = "https://tts.api.cloud.yandex.net/tts/v3/utteranceSynthesis"

# v1 API endpoint - needed for SSML support
TTS_API_V1_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class TTSRequest:
    """Parameters for a TTS synthesis request"""
    text: str | None = None
    ssml: str | None = None
    voice: str | None = None
    role: str | None = None
    lang: str = "ru-RU"
    format: str = "oggopus"
    sample_rate_hz: int = 48000  # only matters for raw formats like lpcm
    speed: str | None = None  # "0.8", "1.0", "1.2"

    def __post_init__(self):
        """Validate that either text or ssml is provided, but not both"""
        if not self.text and not self.ssml:
            raise ValueError("Either text or ssml must be provided")
        if self.text and self.ssml:
            raise ValueError("Cannot provide both text and ssml")

    def is_ssml(self) -> bool:
        """Check if this request is for SSML synthesis"""
        return self.ssml is not None

    def to_payload_v3(self) -> dict[str, Any]:
        """Build the JSON that SpeechKit v3 expects.
        
        Note: Each hint must be its own object with a single field.
        Don't try to combine them - the API will reject it.
        """
        if self.ssml:
            raise ValueError("SSML is not supported in v3 API")
            
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

    def to_form_data_v1(self) -> dict[str, str]:
        """Build form data for SpeechKit v1 API"""
        data = {
            "lang": self.lang,
            "format": self.format,
        }
        
        # Add folder_id if available
        if CONFIG.yandex_folder_id:
            data["folderId"] = CONFIG.yandex_folder_id
        
        if self.ssml:
            data["ssml"] = self.ssml
        else:
            data["text"] = self.text or ""
            
        if self.voice:
            data["voice"] = self.voice
            
        if self.role and self.role.lower() != "neutral":
            data["emotion"] = self.role
            
        if self.speed:
            data["speed"] = str(self.speed)
            
        if self.format == "lpcm":
            data["sampleRateHertz"] = str(self.sample_rate_hz)
            
        logger.info("TTS v1 form data: %s", data)
        return data


class SpeechService:
    """Handles TTS requests to Yandex SpeechKit"""

    def __init__(self) -> None:
        # Not actually used anymore, kept for compatibility
        self._headers = {
            "Authorization": f"Api-Key {CONFIG.yandex_api_key}",
            "Content-Type": "application/json"
        }

    async def synthesize(self, text: str | None = None, ssml: str | None = None, 
                        voice: str | None = None, role: str | None = None, 
                        speed: str | None = None) -> bytes:
        """Convert text or SSML to speech audio.
        
        Args:
            text: Plain text to synthesize (uses v3 API)
            ssml: SSML-formatted text to synthesize (uses v1 API)
            voice: Voice to use
            role: Emotion/role to use
            speed: Speech speed
            
        Returns:
            Raw audio bytes ready to send to Telegram.
        """
        req = TTSRequest(
            text=text,
            ssml=ssml,
            voice=voice or CONFIG.default_voice,
            role=role or CONFIG.default_role,
            speed=speed or CONFIG.default_speed,
            format=CONFIG.default_format,
        )
        
        if req.is_ssml():
            return await self._synthesize_v1(req)
        else:
            return await self._synthesize_v3(req)

    async def _synthesize_v1(self, req: TTSRequest) -> bytes:
        """Use v1 API for SSML synthesis"""
        if not CONFIG.yandex_folder_id:
            raise RuntimeError(
                "SSML synthesis requires YANDEX_FOLDER_ID to be set in environment variables. "
                "Please add your Yandex Cloud folder ID to the .env file."
            )
            
        headers = {"Authorization": f"Api-Key {CONFIG.yandex_api_key}"}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # v1 uses form data, not JSON
            form_data = aiohttp.FormData()
            for key, value in req.to_form_data_v1().items():
                form_data.add_field(key, value)
                
            async with session.post(TTS_API_V1_URL, data=form_data, 
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    detail = await resp.text()
                    if "UNAUTHORIZED" in detail:
                        raise RuntimeError(
                            f"TTS v1 authentication failed. Please check your YANDEX_API_KEY and YANDEX_FOLDER_ID. "
                            f"Error: {detail}"
                        )
                    raise RuntimeError(f"TTS v1 request failed: {resp.status} {detail}")

                # v1 API returns raw audio bytes directly
                audio_bytes = await resp.read()
                if not audio_bytes:
                    raise RuntimeError("TTS v1 API returned no audio data")
                    
                return audio_bytes

    async def _synthesize_v3(self, req: TTSRequest) -> bytes:
        """Use v3 API for regular text synthesis"""
        headers = {"Authorization": f"Api-Key {CONFIG.yandex_api_key}"}

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(TTS_API_URL, json=req.to_payload_v3(), 
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
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
