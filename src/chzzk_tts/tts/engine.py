from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from chzzk_tts.tts.base import TTSProvider, VoiceSettings, detect_language

if TYPE_CHECKING:
    from chzzk_tts.audio.player import AudioPlayer
    from chzzk_tts.db import Database

log = logging.getLogger(__name__)


class TTSEngine(QObject):
    queue_size_changed = Signal(int)
    tts_error = Signal(str)

    def __init__(
        self,
        db: Database,
        audio_player: AudioPlayer,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._db = db
        self._audio_player = audio_player
        self._queue: asyncio.Queue[tuple[str, str, str]] = asyncio.Queue()
        self._providers: dict[str, TTSProvider] = {}
        self._active_provider: TTSProvider | None = None
        self._default_voices: dict[str, str] = {}
        self._enabled = True
        self._task: asyncio.Task | None = None

    def register_provider(self, provider: TTSProvider) -> None:
        self._providers[provider.name] = provider
        if self._active_provider is None:
            self._active_provider = provider

    def set_provider(self, name: str) -> None:
        if name in self._providers:
            self._active_provider = self._providers[name]

    def set_default_voice(self, language: str, voice_id: str) -> None:
        self._default_voices[language] = voice_id

    @property
    def active_provider(self) -> TTSProvider | None:
        return self._active_provider

    @property
    def provider_names(self) -> list[str]:
        return list(self._providers.keys())

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def enqueue(self, user_id: str, nickname: str, content: str) -> None:
        if not self._enabled:
            return
        self._queue.put_nowait((user_id, nickname, content))
        self.queue_size_changed.emit(self._queue.qsize())

    def clear_queue(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self.queue_size_changed.emit(0)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.ensure_future(self._consumer())

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()

    async def _consumer(self) -> None:
        while True:
            try:
                user_id, nickname, content = await self._queue.get()
                self.queue_size_changed.emit(self._queue.qsize())

                if not self._active_provider:
                    continue

                provider = self._active_provider
                language = detect_language(content)

                # Look up user-specific voice settings (per language)
                settings = self._db.get_user_settings(user_id, provider.name, language)
                if settings is None:
                    settings = provider.get_default_settings(language)
                    if language in self._default_voices:
                        settings.voice_id = self._default_voices[language]
                    self._db.save_user_settings(user_id, nickname, settings, language)

                try:
                    samples = await provider.synthesize(content, settings)
                    self._audio_player.enqueue(samples, provider.sample_rate)
                except Exception as e:
                    log.exception("TTS synthesis error")
                    self.tts_error.emit(str(e))

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.exception("TTSEngine consumer error")
                self.tts_error.emit(str(e))
