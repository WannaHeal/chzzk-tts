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
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QScrollArea,
    QFrame,
)

from chzzk_tts.tts.base import VoiceSettings


class LanguageVoiceWidget(QWidget):
    """Widget for configuring voice settings for a specific language."""

    def __init__(
        self, language_code: str, language_name: str, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.language_code = language_code
        self.language_name = language_name
        self._voices: list[dict[str, str]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Voice selector
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(180)
        layout.addRow("음성:", self.voice_combo)

        # Speed
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setMinimum(0.3)
        self.speed_spin.setMaximum(3.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setValue(1.0)
        layout.addRow("속도:", self.speed_spin)

        # Pitch
        self.pitch_spin = QDoubleSpinBox()
        self.pitch_spin.setMinimum(-20.0)
        self.pitch_spin.setMaximum(20.0)
        self.pitch_spin.setSingleStep(1.0)
        self.pitch_spin.setDecimals(1)
        self.pitch_spin.setValue(0.0)
        layout.addRow("피치:", self.pitch_spin)

    def set_voices(self, voices: list[dict[str, str]]) -> None:
        """Set available voices for this language."""
        self._voices = voices
        current_voice = self.voice_combo.currentData()
        self.voice_combo.clear()
        for v in voices:
            self.voice_combo.addItem(v["name"], v["id"])
        # Restore previous selection if possible
        if current_voice:
            for i in range(self.voice_combo.count()):
                if self.voice_combo.itemData(i) == current_voice:
                    self.voice_combo.setCurrentIndex(i)
                    break

    def load_settings(self, settings: VoiceSettings) -> None:
        """Load voice settings."""
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemData(i) == settings.voice_id:
                self.voice_combo.setCurrentIndex(i)
                break
        self.speed_spin.setValue(settings.speed)
        self.pitch_spin.setValue(settings.pitch)

    def get_settings(self, provider_name: str) -> VoiceSettings:
        """Get current voice settings."""
        return VoiceSettings(
            provider_name=provider_name,
            voice_id=self.voice_combo.currentData() or "",
            speed=self.speed_spin.value(),
            pitch=self.pitch_spin.value(),
        )

    def randomize(self) -> None:
        """Randomize settings."""
        if self._voices:
            idx = random.randint(0, len(self._voices) - 1)
            self.voice_combo.setCurrentIndex(idx)
        self.speed_spin.setValue(round(random.gauss(1.0, 0.2), 1))
        self.pitch_spin.setValue(round(random.gauss(0.0, 5.0), 1))

    def reset(self) -> None:
        """Reset to defaults."""
        if self.voice_combo.count() > 0:
            self.voice_combo.setCurrentIndex(0)
        self.speed_spin.setValue(1.0)
        self.pitch_spin.setValue(0.0)


class UserPanel(QWidget):
    """Three-column user voice customization panel.

    Left: Active users from chat (auto-populated)
    Middle: Stored/pinned users (persisted in DB)
    Right: Voice customization settings for all languages
    """

    # user_id, language_code, VoiceSettings
    settings_updated = Signal(str, str, object)
    user_added = Signal(str, str)  # user_id, nickname (add to stored)
    user_removed = Signal(str)  # user_id (remove from stored)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._current_user_id: str = ""
        self._current_provider: str = ""
        self._active_users: dict[str, str] = {}  # user_id -> nickname
        self._stored_users: dict[str, str] = {}  # user_id -> nickname
        self._lang_widgets: dict[str, LanguageVoiceWidget] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)

        # Use splitter for resizable columns
        splitter = QSplitter()

        # === LEFT COLUMN: Active Users ===
        active_group = QGroupBox("채팅 참여자")
        active_layout = QVBoxLayout(active_group)

        self.active_list = QListWidget()
        self.active_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.active_list.itemClicked.connect(self._on_active_selected)
        active_layout.addWidget(self.active_list)

        # Add user button
        self.add_btn = QPushButton("→ 저장")
        self.add_btn.setToolTip("선택한 사용자를 저장 목록에 추가")
        self.add_btn.clicked.connect(self._on_add_user)
        active_layout.addWidget(self.add_btn)

        # Clear button moved to left side
        self.clear_active_btn = QPushButton("채팅 목록 비우기")
        self.clear_active_btn.setToolTip("채팅 참여자 목록 비우기")
        self.clear_active_btn.clicked.connect(self._clear_active_users)
        active_layout.addWidget(self.clear_active_btn)

        active_layout.addWidget(QLabel("최근 채팅 참여자 (최대 50명)"))
        active_layout.addWidget(QLabel("더블클릭으로 빠른 추가"))
        self.active_list.itemDoubleClicked.connect(self._on_add_user)

        splitter.addWidget(active_group)

        # === MIDDLE COLUMN: Stored Users ===
        stored_group = QGroupBox("저장된 사용자")
        stored_layout = QVBoxLayout(stored_group)

        self.stored_list = QListWidget()
        self.stored_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.stored_list.currentItemChanged.connect(self._on_stored_selection_changed)
        stored_layout.addWidget(self.stored_list)

        self.remove_btn = QPushButton("제거")
        self.remove_btn.setToolTip("선택한 사용자를 저장 목록에서 제거")
        self.remove_btn.clicked.connect(self._on_remove_user)
        stored_layout.addWidget(self.remove_btn)

        stored_layout.addWidget(QLabel("음성 커스터마이징 대상"))

        splitter.addWidget(stored_group)

        # === RIGHT COLUMN: Voice Customization (All Languages) ===
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)

        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        # Korean voice settings
        ko_group = QGroupBox("한국어 (ko-KR)")
        ko_layout = QVBoxLayout(ko_group)
        self.ko_widget = LanguageVoiceWidget("ko-KR", "한국어")
        ko_layout.addWidget(self.ko_widget)
        settings_layout.addWidget(ko_group)
        self._lang_widgets["ko-KR"] = self.ko_widget

        # Japanese voice settings
        ja_group = QGroupBox("일본어 (ja-JP)")
        ja_layout = QVBoxLayout(ja_group)
        self.ja_widget = LanguageVoiceWidget("ja-JP", "일본어")
        ja_layout.addWidget(self.ja_widget)
        settings_layout.addWidget(ja_group)
        self._lang_widgets["ja-JP"] = self.ja_widget

        # English voice settings
        en_group = QGroupBox("영어 (en-US)")
        en_layout = QVBoxLayout(en_group)
        self.en_widget = LanguageVoiceWidget("en-US", "영어")
        en_layout.addWidget(self.en_widget)
        settings_layout.addWidget(en_group)
        self._lang_widgets["en-US"] = self.en_widget

        # Action buttons
        action_group = QGroupBox("작업")
        action_layout = QHBoxLayout(action_group)

        self.update_btn = QPushButton("모두 업데이트")
        self.update_btn.setToolTip("모든 언어 설정 저장")
        self.randomize_btn = QPushButton("랜덤")
        self.randomize_btn.setToolTip("무작위 음성 설정")
        self.reset_btn = QPushButton("초기화")
        self.reset_btn.setToolTip("기본값으로 초기화")

        action_layout.addWidget(self.update_btn)
        action_layout.addWidget(self.randomize_btn)
        action_layout.addWidget(self.reset_btn)
        action_layout.addStretch()

        settings_layout.addWidget(action_group)

        # Info label for feedback (inside the third panel)
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        settings_layout.addWidget(self.info_label)

        settings_layout.addStretch()

        # Connect buttons
        self.update_btn.clicked.connect(self._on_update)
        self.randomize_btn.clicked.connect(self._on_randomize)
        self.reset_btn.clicked.connect(self._on_reset)

        settings_scroll.setWidget(settings_widget)
        splitter.addWidget(settings_scroll)

        # Set initial splitter sizes (approximate ratios)
        splitter.setSizes([200, 200, 400])

        main_layout.addWidget(splitter)

    def set_voices(
        self,
        voices_ko: list[dict[str, str]],
        voices_ja: list[dict[str, str]],
        voices_en: list[dict[str, str]],
        provider: str,
    ) -> None:
        """Set available voices for all languages."""
        self._current_provider = provider
        self.ko_widget.set_voices(voices_ko)
        self.ja_widget.set_voices(voices_ja)
        self.en_widget.set_voices(voices_en)

    def add_active_user(self, user_id: str, nickname: str) -> None:
        """Add a user to the active chat users list."""
        if user_id not in self._active_users:
            self._active_users[user_id] = nickname
            display_text = f"{nickname}"
            item = QListWidgetItem(display_text)
            item.setData(0x100, user_id)  # Store user_id as item data
            item.setToolTip(f"ID: {user_id}")
            self.active_list.addItem(item)

            # Limit to 50 most recent users
            while self.active_list.count() > 50:
                removed_item = self.active_list.takeItem(0)
                if removed_item:
                    removed_id = removed_item.data(0x100)
                    self._active_users.pop(removed_id, None)

    def clear_active_users(self) -> None:
        """Clear the active users list."""
        self._active_users.clear()
        self.active_list.clear()

    def _clear_active_users(self) -> None:
        """Clear active users button handler."""
        self.clear_active_users()

    def set_stored_users(self, users: list[tuple[str, str]]) -> None:
        """Set the stored/pinned users list from database."""
        self._stored_users = {uid: nick for uid, nick in users}
        self._refresh_stored_list()

        # Restore selection if possible
        if self._current_user_id and self._current_user_id in self._stored_users:
            self.select_stored_user(self._current_user_id)

    def _refresh_stored_list(self) -> None:
        """Refresh the stored users list widget."""
        self.stored_list.clear()
        for user_id, nickname in sorted(
            self._stored_users.items(), key=lambda x: x[1].lower()
        ):
            display_text = f"{nickname}"
            item = QListWidgetItem(display_text)
            item.setData(0x100, user_id)
            item.setToolTip(f"ID: {user_id}")
            self.stored_list.addItem(item)

    def select_stored_user(self, user_id: str) -> None:
        """Select a specific user in the stored list."""
        for i in range(self.stored_list.count()):
            item = self.stored_list.item(i)
            if item and item.data(0x100) == user_id:
                self.stored_list.setCurrentItem(item)
                break

    def load_language_settings(
        self, language_code: str, settings: VoiceSettings
    ) -> None:
        """Load voice settings for a specific language."""
        widget = self._lang_widgets.get(language_code)
        if widget:
            widget.load_settings(settings)

    def _get_all_settings(self) -> dict[str, VoiceSettings]:
        """Get current voice settings for all languages."""
        return {
            code: widget.get_settings(self._current_provider)
            for code, widget in self._lang_widgets.items()
        }

    def _on_active_selected(self, item: QListWidgetItem) -> None:
        """Handle selection of an active user."""
        pass  # Just visual feedback, add button does the work

    def _on_add_user(self) -> None:
        """Add selected active user to stored users."""
        item = self.active_list.currentItem()
        if item is None:
            # Try double-clicked item
            item = self.active_list.item(self.active_list.currentRow())
            if item is None:
                return

        user_id = item.data(0x100)
        nickname = self._active_users.get(user_id, "")

        if user_id and user_id not in self._stored_users:
            self.user_added.emit(user_id, nickname)

    def _on_remove_user(self) -> None:
        """Remove selected user from stored users."""
        item = self.stored_list.currentItem()
        if item:
            user_id = item.data(0x100)
            if user_id:
                self.user_removed.emit(user_id)

    def _on_stored_selection_changed(
        self, current: QListWidgetItem, previous: QListWidgetItem
    ) -> None:
        """Handle selection change in stored users list."""
        if current:
            self._current_user_id = current.data(0x100)
        else:
            self._current_user_id = ""

    def get_current_user_id(self) -> str:
        """Get currently selected stored user ID."""
        return self._current_user_id

    def _on_update(self) -> None:
        """Update settings for all languages."""
        if self._current_user_id:
            settings_dict = self._get_all_settings()
            for lang_code, settings in settings_dict.items():
                self.settings_updated.emit(self._current_user_id, lang_code, settings)
            self.info_label.setText("모든 언어 설정이 업데이트되었습니다.")

    def _on_randomize(self) -> None:
        """Randomize settings for all languages."""
        for widget in self._lang_widgets.values():
            widget.randomize()
        self._on_update()

    def _on_reset(self) -> None:
        """Reset all languages to defaults."""
        for widget in self._lang_widgets.values():
            widget.reset()
        self._on_update()
