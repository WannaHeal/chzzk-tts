from __future__ import annotations

import io
from typing import Any

import edge_tts
import numpy as np
import soundfile as sf

from chzzk_tts.tts.base import TTSProvider, VoiceSettings, detect_language

# Default voices per language
_DEFAULT_VOICES = {
    "ko-KR": "ko-KR-SunHiNeural",
    "ja-JP": "ja-JP-NanamiNeural",
    "en-US": "en-US-AriaNeural",
}

_VOICES_BY_LANG: dict[str, list[dict[str, str]]] = {
    "ko-KR": [
        {"id": "ko-KR-SunHiNeural", "name": "SunHi (여성)"},
        {"id": "ko-KR-InJoonNeural", "name": "InJoon (남성)"},
        {"id": "ko-KR-HyunsuMultilingualNeural", "name": "Hyunsu Multilingual (남성)"},
    ],
    "ja-JP": [
        {"id": "ja-JP-NanamiNeural", "name": "Nanami (女性)"},
        {"id": "ja-JP-KeitaNeural", "name": "Keita (男性)"},
    ],
    "en-US": [
        {"id": "en-US-AnaNeural", "name": "Ana (Female) - Cartoon"},
        {"id": "en-US-AndrewMultilingualNeural", "name": "Andrew Multilingual (Male)"},
        {"id": "en-US-AndrewNeural", "name": "Andrew (Male)"},
        {"id": "en-US-AriaNeural", "name": "Aria (Female) - News"},
        {"id": "en-US-AvaMultilingualNeural", "name": "Ava Multilingual (Female)"},
        {"id": "en-US-AvaNeural", "name": "Ava (Female)"},
        {"id": "en-US-BrianMultilingualNeural", "name": "Brian Multilingual (Male)"},
        {"id": "en-US-BrianNeural", "name": "Brian (Male)"},
        {"id": "en-US-ChristopherNeural", "name": "Christopher (Male) - News"},
        {"id": "en-US-EmmaMultilingualNeural", "name": "Emma Multilingual (Female)"},
        {"id": "en-US-EmmaNeural", "name": "Emma (Female)"},
        {"id": "en-US-EricNeural", "name": "Eric (Male) - News"},
        {"id": "en-US-GuyNeural", "name": "Guy (Male) - News"},
        {"id": "en-US-JennyNeural", "name": "Jenny (Female) - General"},
        {"id": "en-US-MichelleNeural", "name": "Michelle (Female) - News"},
        {"id": "en-US-RogerNeural", "name": "Roger (Male) - News"},
        {"id": "en-US-SteffanNeural", "name": "Steffan (Male) - News"},
    ],
}


class EdgeTTSProvider(TTSProvider):
    @property
    def name(self) -> str:
        return "edge"

    @property
    def sample_rate(self) -> int:
        return 24000

    async def synthesize(self, text: str, settings: VoiceSettings) -> np.ndarray:
        rate_str = f"{int((settings.speed - 1.0) * 100):+d}%"
        pitch_str = f"{int(settings.pitch):+d}Hz"

        communicate = edge_tts.Communicate(
            text=text,
            voice=settings.voice_id,
            rate=rate_str,
            pitch=pitch_str,
        )

        mp3_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_data.extend(chunk["data"])

        # Read MP3 data using soundfile
        # edge-tts returns audio-24khz-48kbitrate-mono-mp3
        audio_buffer = io.BytesIO(bytes(mp3_data))
        audio_data, _original_sr = sf.read(audio_buffer, dtype="int16")

        return audio_data

    def get_available_voices(self, language: str | None = None) -> list[dict[str, str]]:
        if language and language in _VOICES_BY_LANG:
            return _VOICES_BY_LANG[language]
        result = []
        for voices in _VOICES_BY_LANG.values():
            result.extend(voices)
        return result

    def get_default_settings(self, language: str = "ko-KR") -> VoiceSettings:
        voice_id = _DEFAULT_VOICES.get(language, _DEFAULT_VOICES["ko-KR"])
        return VoiceSettings(
            provider_name=self.name,
            voice_id=voice_id,
            speed=1.0,
            pitch=0.0,
        )
