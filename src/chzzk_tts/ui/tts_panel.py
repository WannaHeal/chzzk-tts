from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QCheckBox,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QSlider,
    QLabel,
    QPushButton,
    QSpinBox,
    QGroupBox,
    QFileDialog,
    QLineEdit,
)


class TTSPanel(QWidget):
    tts_enabled_changed = Signal(bool)
    provider_changed = Signal(str)
    playback_mode_changed = Signal(str)  # "sequential" or "interrupt"
    volume_changed = Signal(float)
    max_length_changed = Signal(int)
    skip_commands_changed = Signal(bool)
    clear_queue_requested = Signal()
    google_credentials_changed = Signal(str)
    default_voice_changed = Signal(str, str)  # language, voice_id

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # TTS Enable
        self.tts_checkbox = QCheckBox("TTS 활성화")
        self.tts_checkbox.setChecked(True)
        self.tts_checkbox.stateChanged.connect(
            lambda state: self.tts_enabled_changed.emit(state == Qt.CheckState.Checked.value)
        )
        layout.addWidget(self.tts_checkbox)

        # Provider selection
        provider_group = QGroupBox("TTS 제공자")
        provider_layout = QFormLayout()

        self.provider_combo = QComboBox()
        self.provider_combo.currentTextChanged.connect(self.provider_changed.emit)
        provider_layout.addRow("제공자:", self.provider_combo)

        # Google credentials
        cred_layout = QHBoxLayout()
        self.cred_path_edit = QLineEdit()
        self.cred_path_edit.setPlaceholderText("Google TTS 인증 JSON 파일 경로")
        self.cred_path_edit.setReadOnly(True)
        cred_layout.addWidget(self.cred_path_edit)

        self.cred_browse_btn = QPushButton("찾아보기")
        self.cred_browse_btn.clicked.connect(self._browse_credentials)
        cred_layout.addWidget(self.cred_browse_btn)

        provider_layout.addRow("Google 인증:", cred_layout)
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # Default voices per language
        default_voice_group = QGroupBox("기본 음성")
        default_voice_layout = QFormLayout()

        self.ko_voice_combo = QComboBox()
        self.ko_voice_combo.currentIndexChanged.connect(
            lambda _: self.default_voice_changed.emit(
                "ko-KR", self.ko_voice_combo.currentData() or ""
            )
        )
        default_voice_layout.addRow("한국어:", self.ko_voice_combo)

        self.ja_voice_combo = QComboBox()
        self.ja_voice_combo.currentIndexChanged.connect(
            lambda _: self.default_voice_changed.emit(
                "ja-JP", self.ja_voice_combo.currentData() or ""
            )
        )
        default_voice_layout.addRow("일본어:", self.ja_voice_combo)

        self.en_voice_combo = QComboBox()
        self.en_voice_combo.currentIndexChanged.connect(
            lambda _: self.default_voice_changed.emit(
                "en-US", self.en_voice_combo.currentData() or ""
            )
        )
        default_voice_layout.addRow("영어:", self.en_voice_combo)

        default_voice_group.setLayout(default_voice_layout)
        layout.addWidget(default_voice_group)

        # Playback mode
        mode_group = QGroupBox("재생 모드")
        mode_layout = QHBoxLayout()

        self.mode_group = QButtonGroup(self)
        self.sequential_radio = QRadioButton("순차 재생")
        self.sequential_radio.setChecked(True)
        self.interrupt_radio = QRadioButton("끊고 재생")
        self.mode_group.addButton(self.sequential_radio)
        self.mode_group.addButton(self.interrupt_radio)

        mode_layout.addWidget(self.sequential_radio)
        mode_layout.addWidget(self.interrupt_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        self.sequential_radio.toggled.connect(
            lambda checked: self.playback_mode_changed.emit(
                "sequential" if checked else "interrupt"
            )
        )

        # Volume
        vol_group = QGroupBox("볼륨")
        vol_layout = QHBoxLayout()

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(-30)
        self.volume_slider.setMaximum(30)
        self.volume_slider.setValue(0)
        self.volume_label = QLabel("0 dB")

        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        vol_layout.addWidget(self.volume_slider)
        vol_layout.addWidget(self.volume_label)
        vol_group.setLayout(vol_layout)
        layout.addWidget(vol_group)

        # Message settings
        msg_group = QGroupBox("메시지 설정")
        msg_layout = QFormLayout()

        self.max_length_spin = QSpinBox()
        self.max_length_spin.setMinimum(10)
        self.max_length_spin.setMaximum(200)
        self.max_length_spin.setValue(50)
        self.max_length_spin.valueChanged.connect(self.max_length_changed.emit)
        msg_layout.addRow("최대 글자 수:", self.max_length_spin)

        self.skip_commands_check = QCheckBox("명령어 스킵 (! 로 시작)")
        self.skip_commands_check.setChecked(True)
        self.skip_commands_check.stateChanged.connect(
            lambda state: self.skip_commands_changed.emit(state == Qt.CheckState.Checked.value)
        )
        msg_layout.addRow(self.skip_commands_check)

        msg_group.setLayout(msg_layout)
        layout.addWidget(msg_group)

        # Queue controls
        queue_layout = QHBoxLayout()
        self.queue_label = QLabel("대기열: 0")
        self.clear_queue_btn = QPushButton("큐 비우기")
        self.clear_queue_btn.clicked.connect(self.clear_queue_requested.emit)
        queue_layout.addWidget(self.queue_label)
        queue_layout.addWidget(self.clear_queue_btn)
        queue_layout.addStretch()
        layout.addLayout(queue_layout)

        layout.addStretch()

    def _on_volume_changed(self, value: int) -> None:
        self.volume_label.setText(f"{value} dB")
        self.volume_changed.emit(float(value))

    def _browse_credentials(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Google TTS 인증 파일 선택", ".", "JSON (*.json)"
        )
        if path:
            self.cred_path_edit.setText(path)
            self.google_credentials_changed.emit(path)

    def set_default_voice_options(
        self,
        ko_voices: list[dict[str, str]],
        ja_voices: list[dict[str, str]],
        en_voices: list[dict[str, str]],
    ) -> None:
        for combo, voices in [
            (self.ko_voice_combo, ko_voices),
            (self.ja_voice_combo, ja_voices),
            (self.en_voice_combo, en_voices),
        ]:
            combo.blockSignals(True)
            combo.clear()
            for v in voices:
                combo.addItem(v["name"], v["id"])
            combo.blockSignals(False)

    def load_default_voices(self, ko_voice_id: str, ja_voice_id: str, en_voice_id: str) -> None:
        for combo, voice_id in [
            (self.ko_voice_combo, ko_voice_id),
            (self.ja_voice_combo, ja_voice_id),
            (self.en_voice_combo, en_voice_id),
        ]:
            for i in range(combo.count()):
                if combo.itemData(i) == voice_id:
                    combo.setCurrentIndex(i)
                    break

    def set_providers(self, names: list[str]) -> None:
        self.provider_combo.clear()
        for name in names:
            display = {"edge": "Edge TTS (무료)", "google": "Google Cloud TTS"}.get(
                name, name
            )
            self.provider_combo.addItem(display, name)

    def set_queue_size(self, size: int) -> None:
        self.queue_label.setText(f"대기열: {size}")

    def load_config(
        self,
        tts_enabled: bool,
        provider: str,
        playback_mode: str,
        volume_db: float,
        max_length: int,
        skip_commands: bool,
        google_cred_path: str,
        default_voice_ko: str = "",
        default_voice_ja: str = "",
        default_voice_en: str = "",
    ) -> None:
        self.tts_checkbox.setChecked(tts_enabled)
        # Set provider by data
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider:
                self.provider_combo.setCurrentIndex(i)
                break
        if playback_mode == "interrupt":
            self.interrupt_radio.setChecked(True)
        else:
            self.sequential_radio.setChecked(True)
        self.volume_slider.setValue(int(volume_db))
        self.max_length_spin.setValue(max_length)
        self.skip_commands_check.setChecked(skip_commands)
        self.cred_path_edit.setText(google_cred_path)
        if default_voice_ko:
            self.load_default_voices(default_voice_ko, default_voice_ja, default_voice_en)

    def current_provider_data(self) -> str:
        return self.provider_combo.currentData() or "edge"
