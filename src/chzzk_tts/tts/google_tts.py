from __future__ import annotations

import asyncio
import os
import struct
from typing import Any

import numpy as np

from chzzk_tts.tts.base import TTSProvider, VoiceSettings, detect_language

_DEFAULT_VOICES = {
    "ko-KR": [
        {"id": "ko-KR-Standard-A", "name": "Standard A (여성)"},
        {"id": "ko-KR-Standard-B", "name": "Standard B (여성)"},
        {"id": "ko-KR-Standard-C", "name": "Standard C (남성)"},
        {"id": "ko-KR-Standard-D", "name": "Standard D (남성)"},
        {"id": "ko-KR-Wavenet-A", "name": "Wavenet A (여성)"},
        {"id": "ko-KR-Wavenet-B", "name": "Wavenet B (여성)"},
        {"id": "ko-KR-Wavenet-C", "name": "Wavenet C (남성)"},
        {"id": "ko-KR-Wavenet-D", "name": "Wavenet D (남성)"},
    ],
    "ja-JP": [
        {"id": "ja-JP-Standard-A", "name": "Standard A (女性)"},
        {"id": "ja-JP-Standard-B", "name": "Standard B (女性)"},
        {"id": "ja-JP-Standard-C", "name": "Standard C (男性)"},
        {"id": "ja-JP-Standard-D", "name": "Standard D (男性)"},
        {"id": "ja-JP-Wavenet-A", "name": "Wavenet A (女性)"},
        {"id": "ja-JP-Wavenet-B", "name": "Wavenet B (女性)"},
        {"id": "ja-JP-Wavenet-C", "name": "Wavenet C (男性)"},
        {"id": "ja-JP-Wavenet-D", "name": "Wavenet D (男性)"},
    ],
    "en-US": [
        {"id": "en-US-Standard-C", "name": "Standard C (Female)"},
        {"id": "en-US-Standard-E", "name": "Standard E (Female)"},
        {"id": "en-US-Standard-A", "name": "Standard A (Male)"},
        {"id": "en-US-Standard-B", "name": "Standard B (Male)"},
        {"id": "en-US-Wavenet-C", "name": "Wavenet C (Female)"},
        {"id": "en-US-Wavenet-E", "name": "Wavenet E (Female)"},
        {"id": "en-US-Wavenet-A", "name": "Wavenet A (Male)"},
        {"id": "en-US-Wavenet-B", "name": "Wavenet B (Male)"},
    ],
}


class GoogleCloudTTSProvider(TTSProvider):
    def __init__(self, credentials_path: str = ""):
        self._client = None
        self._credentials_path = credentials_path

    def _ensure_client(self):
        if self._client is not None:
            return
        if self._credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self._credentials_path
        from google.cloud import texttospeech
        self._client = texttospeech.TextToSpeechClient()

    def set_credentials(self, path: str) -> None:
        self._credentials_path = path
        self._client = None  # force re-creation

    @property
    def name(self) -> str:
        return "google"

    @property
    def sample_rate(self) -> int:
        return 24000

    def _synthesize_sync(self, text: str, settings: VoiceSettings) -> bytes:
        from google.cloud import texttospeech

        self._ensure_client()

        lang_code = settings.voice_id.rsplit("-", 2)[0]  # "ko-KR-Standard-A" -> "ko-KR"
        # Try to extract language from voice_id pattern
        parts = settings.voice_id.split("-")
        if len(parts) >= 2:
            lang_code = f"{parts[0]}-{parts[1]}"

        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=settings.voice_id,
        )

        # pitch: 0.0-2.0 mapped to -20.0 to +20.0 semitones
        pitch_semitones = settings.pitch * 20.0 - 20.0

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=settings.speed,
            pitch=pitch_semitones,
            sample_rate_hertz=self.sample_rate,
        )

        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self._client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return response.audio_content

    async def synthesize(self, text: str, settings: VoiceSettings) -> np.ndarray:
        wav_bytes = await asyncio.to_thread(self._synthesize_sync, text, settings)
        # Skip WAV header (44 bytes) to get raw PCM s16le
        pcm_data = wav_bytes[44:]
        samples = np.frombuffer(pcm_data, dtype=np.int16)
        return samples

    def get_available_voices(self, language: str | None = None) -> list[dict[str, str]]:
        if language and language in _DEFAULT_VOICES:
            return _DEFAULT_VOICES[language]
        result = []
        for voices in _DEFAULT_VOICES.values():
            result.extend(voices)
        return result

    def get_default_settings(self, language: str = "ko-KR") -> VoiceSettings:
        voices = _DEFAULT_VOICES.get(language, _DEFAULT_VOICES["ko-KR"])
        return VoiceSettings(
            provider_name=self.name,
            voice_id=voices[0]["id"],
            speed=1.0,
            pitch=1.0,  # 1.0 = 0 semitones (neutral)
        )
