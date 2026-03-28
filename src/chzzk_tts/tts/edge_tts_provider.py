from __future__ import annotations

import io
from typing import Any

import edge_tts
import numpy as np
from pydub import AudioSegment

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
        {"id": "ko-KR-BongJinNeural", "name": "BongJin (남성)"},
        {"id": "ko-KR-GookMinNeural", "name": "GookMin (남성)"},
        {"id": "ko-KR-HyunsuNeural", "name": "Hyunsu (남성)"},
        {"id": "ko-KR-JiMinNeural", "name": "JiMin (여성)"},
        {"id": "ko-KR-SeoHyeonNeural", "name": "SeoHyeon (여성)"},
        {"id": "ko-KR-SoonBokNeural", "name": "SoonBok (여성)"},
        {"id": "ko-KR-YuJinNeural", "name": "YuJin (여성)"},
    ],
    "ja-JP": [
        {"id": "ja-JP-NanamiNeural", "name": "Nanami (女性)"},
        {"id": "ja-JP-KeitaNeural", "name": "Keita (男性)"},
        {"id": "ja-JP-AoiNeural", "name": "Aoi (女性)"},
        {"id": "ja-JP-DaichiNeural", "name": "Daichi (男性)"},
    ],
    "en-US": [
        {"id": "en-US-AriaNeural", "name": "Aria (Female)"},
        {"id": "en-US-GuyNeural", "name": "Guy (Male)"},
        {"id": "en-US-JennyNeural", "name": "Jenny (Female)"},
        {"id": "en-US-ChristopherNeural", "name": "Christopher (Male)"},
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

        audio_seg = AudioSegment.from_file(io.BytesIO(bytes(mp3_data)), format="mp3")
        audio_seg = audio_seg.set_frame_rate(self.sample_rate).set_channels(1)
        samples = np.array(audio_seg.get_array_of_samples(), dtype=np.int16)
        return samples

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
