from __future__ import annotations

import random

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QGroupBox,
    QLabel,
)

from chzzk_tts.tts.base import VoiceSettings


class UserPanel(QWidget):
    settings_updated = Signal(str, object)  # user_id, VoiceSettings
    language_changed = Signal(str)  # language code

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_user_id: str = ""
        self._current_provider: str = ""
        self._voices: list[dict[str, str]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # User selector
        user_group = QGroupBox("사용자 선택")
        user_layout = QHBoxLayout()

        self.user_combo = QComboBox()
        self.user_combo.setMinimumWidth(200)
        self.user_combo.currentIndexChanged.connect(self._on_user_changed)
        user_layout.addWidget(self.user_combo)

        self.refresh_btn = QPushButton("새로고침")
        user_layout.addWidget(self.refresh_btn)
        user_layout.addStretch()

        user_group.setLayout(user_layout)
        layout.addWidget(user_group)

        # Voice settings
        voice_group = QGroupBox("음성 설정")
        voice_layout = QFormLayout()

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("한국어", "ko-KR")
        self.lang_combo.addItem("일본어", "ja-JP")
        self.lang_combo.addItem("영어", "en-US")
        self.lang_combo.currentIndexChanged.connect(
            lambda _: self.language_changed.emit(self.lang_combo.currentData())
        )
        voice_layout.addRow("언어:", self.lang_combo)

        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(250)
        voice_layout.addRow("음성:", self.voice_combo)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setMinimum(0.3)
        self.speed_spin.setMaximum(3.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setValue(1.0)
        voice_layout.addRow("속도:", self.speed_spin)

        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setMinimum(-20.0)
        self.pitch_spin.setMaximum(20.0)
        self.pitch_spin.setSingleStep(1.0)
        self.pitch_spin.setDecimals(1)
        self.pitch_spin.setValue(0.0)
        voice_layout.addRow("피치:", self.pitch_spin)

        self.info_label = QLabel("")
        voice_layout.addRow(self.info_label)

        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.update_btn = QPushButton("업데이트")
        self.randomize_btn = QPushButton("랜덤")
        self.reset_btn = QPushButton("초기화")

        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.randomize_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        # Connect buttons
        self.update_btn.clicked.connect(self._on_update)
        self.randomize_btn.clicked.connect(self._on_randomize)
        self.reset_btn.clicked.connect(self._on_reset)

    def current_language(self) -> str:
        return self.lang_combo.currentData() or "ko-KR"

    def set_voices(self, voices: list[dict[str, str]], provider: str) -> None:
        self._voices = voices
        self._current_provider = provider
        self.voice_combo.clear()
        for v in voices:
            self.voice_combo.addItem(v["name"], v["id"])

    def set_users(self, users: list[tuple[str, str]]) -> None:
        old_id = self._current_user_id
        self.user_combo.clear()
        for user_id, nickname in users:
            display = f"{nickname} ({user_id[:8]}...)" if len(user_id) > 8 else f"{nickname} ({user_id})"
            self.user_combo.addItem(display, user_id)
        # Restore selection
        for i in range(self.user_combo.count()):
            if self.user_combo.itemData(i) == old_id:
                self.user_combo.setCurrentIndex(i)
                break

    def load_settings(self, settings: VoiceSettings) -> None:
        # Set voice combo
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i) == settings.voice_id:
                self.voice_combo.setCurrentIndex(i)
                break
        self.speed_spin.setValue(settings.speed)
        self.pitch_spin.setValue(settings.pitch)

    def _on_user_changed(self, index: int) -> None:
        if index >= 0:
            self._current_user_id = self.user_combo.itemData(index) or ""

    def _get_current_settings(self) -> VoiceSettings:
        return VoiceSettings(
            provider_name=self._current_provider,
            voice_id=self.voice_combo.currentData() or "",
            speed=self.speed_spin.value(),
            pitch=self.pitch_spin.value(),
        )

    def _on_update(self) -> None:
        if self._current_user_id:
            self.settings_updated.emit(
                self._current_user_id, self._get_current_settings()
            )
            self.info_label.setText("설정이 업데이트되었습니다.")

    def _on_randomize(self) -> None:
        if self._voices:
            idx = random.randint(0, len(self._voices) - 1)
            self.voice_combo.setCurrentIndex(idx)
        self.speed_spin.setValue(round(random.gauss(1.0, 0.2), 1))
        self.pitch_spin.setValue(round(random.gauss(0.0, 5.0), 1))
        self._on_update()

    def _on_reset(self) -> None:
        if self.voice_combo.count() > 0:
            self.voice_combo.setCurrentIndex(0)
        self.speed_spin.setValue(1.0)
        self.pitch_spin.setValue(0.0)
        self._on_update()
