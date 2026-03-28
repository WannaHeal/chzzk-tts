from __future__ import annotations

import queue
import threading
from enum import Enum

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal


class PlaybackMode(Enum):
    SEQUENTIAL = "sequential"
    INTERRUPT = "interrupt"


class AudioPlayer(QObject):
    playback_started = Signal()
    playback_finished = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._queue: queue.Queue[tuple[np.ndarray, int] | None] = queue.Queue()
        self._mode = PlaybackMode.SEQUENTIAL
        self._volume_db: float = 0.0
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    @property
    def mode(self) -> PlaybackMode:
        return self._mode

    def set_mode(self, mode: PlaybackMode) -> None:
        self._mode = mode

    def set_volume(self, db: float) -> None:
        self._volume_db = db

    def enqueue(self, samples: np.ndarray, sample_rate: int) -> None:
        if self._mode == PlaybackMode.INTERRUPT:
            self.clear()
            sd.stop()
        self._queue.put((samples, sample_rate))

    def clear(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def stop(self) -> None:
        self._running = False
        sd.stop()
        self._queue.put(None)  # sentinel to unblock
        self._thread.join(timeout=3)

    def _apply_volume(self, samples: np.ndarray) -> np.ndarray:
        if self._volume_db == 0.0:
            return samples
        linear = 10.0 ** (self._volume_db / 20.0)
        adjusted = samples.astype(np.float32) * linear
        return np.clip(adjusted, -32768, 32767).astype(np.int16)

    def _worker(self) -> None:
        while self._running:
            item = self._queue.get()
            if item is None:
                break
            samples, sample_rate = item
            samples = self._apply_volume(samples)
            try:
                self.playback_started.emit()
                sd.play(samples, sample_rate)
                sd.wait()
                self.playback_finished.emit()
            except Exception as e:
                print(f"Audio playback error: {e}")
