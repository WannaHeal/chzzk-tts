from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

CONFIG_PATH = Path("config.json")


@dataclass
class AppConfig:
    # CHZZK credentials
    client_id: str = ""
    client_secret: str = ""
    channel_id: str = ""

    # TTS settings
    tts_enabled: bool = True
    tts_provider: str = "edge"  # "google" or "edge"
    playback_mode: str = "sequential"  # "sequential" or "interrupt"
    volume_db: float = 0.0  # -30.0 to +30.0
    max_message_length: int = 50
    skip_commands: bool = True  # skip messages starting with '!'
    skip_emojis: bool = (
        False  # skip messages containing only emojis like {:emoji_name:}
    )

    # Default voices per language (Edge TTS)
    default_voice_ko: str = "ko-KR-SunHiNeural"
    default_voice_ja: str = "ja-JP-NanamiNeural"
    default_voice_en: str = "en-US-AriaNeural"

    # Google TTS
    google_credentials_path: str = ""

    # Database
    db_path: str = "chzzk_tts.db"

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> AppConfig:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                known_fields = {f.name for f in cls.__dataclass_fields__.values()}
                filtered = {k: v for k, v in data.items() if k in known_fields}
                return cls(**filtered)
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self, path: Path = CONFIG_PATH) -> None:
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
