from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

_KOR = re.compile("[ㄱ-ㅎㅏ-ㅣ가-힣]")
_JPN = re.compile("[ぁ-ゔァ-ヴー々〆〤\u4e00-\u9fff]")


def detect_language(text: str) -> str:
    if _KOR.search(text):
        return "ko-KR"
    if _JPN.search(text):
        return "ja-JP"
    return "en-US"


@dataclass
class VoiceSettings:
    provider_name: str
    voice_id: str
    speed: float = 1.0
    pitch: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


class TTSProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        ...

    @abstractmethod
    async def synthesize(self, text: str, settings: VoiceSettings) -> np.ndarray:
        """Return PCM audio as a numpy int16 array."""
        ...

    @abstractmethod
    def get_available_voices(self, language: str | None = None) -> list[dict[str, str]]:
        """Return list of dicts with at least 'id' and 'name' keys."""
        ...

    @abstractmethod
    def get_default_settings(self, language: str = "ko-KR") -> VoiceSettings:
        ...
