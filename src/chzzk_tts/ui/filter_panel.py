from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QGroupBox,
    QSplitter,
)
from PySide6.QtCore import Qt


class FilterPanel(QWidget):
    banned_word_added = Signal(str)
    banned_word_removed = Signal(str)
    banned_user_added = Signal(str)
    banned_user_removed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Banned words
        word_widget = QWidget()
        word_layout = QVBoxLayout(word_widget)
        word_layout.setContentsMargins(0, 0, 0, 0)

        word_group = QGroupBox("금칙어 리스트")
        word_inner = QVBoxLayout()

        self.word_list = QListWidget()
        word_inner.addWidget(self.word_list)

        word_input_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("금칙어 입력...")
        self.word_add_btn = QPushButton("추가")
        self.word_remove_btn = QPushButton("삭제")
        word_input_layout.addWidget(self.word_input)
        word_input_layout.addWidget(self.word_add_btn)
        word_input_layout.addWidget(self.word_remove_btn)
        word_inner.addLayout(word_input_layout)

        word_group.setLayout(word_inner)
        word_layout.addWidget(word_group)
        splitter.addWidget(word_widget)

        # Banned users
        user_widget = QWidget()
        user_layout = QVBoxLayout(user_widget)
        user_layout.setContentsMargins(0, 0, 0, 0)

        user_group = QGroupBox("TTS 밴 리스트")
        user_inner = QVBoxLayout()

        self.user_list = QListWidget()
        user_inner.addWidget(self.user_list)

        user_input_layout = QHBoxLayout()
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("사용자 ID 입력...")
        self.user_add_btn = QPushButton("추가")
        self.user_remove_btn = QPushButton("삭제")
        user_input_layout.addWidget(self.user_input)
        user_input_layout.addWidget(self.user_add_btn)
        user_input_layout.addWidget(self.user_remove_btn)
        user_inner.addLayout(user_input_layout)

        user_group.setLayout(user_inner)
        user_layout.addWidget(user_group)
        splitter.addWidget(user_widget)

        layout.addWidget(splitter)

        # Signals
        self.word_add_btn.clicked.connect(self._add_word)
        self.word_input.returnPressed.connect(self._add_word)
        self.word_remove_btn.clicked.connect(self._remove_word)

        self.user_add_btn.clicked.connect(self._add_user)
        self.user_input.returnPressed.connect(self._add_user)
        self.user_remove_btn.clicked.connect(self._remove_user)

    def _add_word(self) -> None:
        word = self.word_input.text().strip()
        if word:
            self.word_input.clear()
            self.banned_word_added.emit(word)

    def _remove_word(self) -> None:
        item = self.word_list.currentItem()
        if item:
            self.banned_word_removed.emit(item.text())

    def _add_user(self) -> None:
        user_id = self.user_input.text().strip()
        if user_id:
            self.user_input.clear()
            self.banned_user_added.emit(user_id)

    def _remove_user(self) -> None:
        item = self.user_list.currentItem()
        if item:
            self.banned_user_removed.emit(item.text())

    def set_banned_words(self, words: list[str]) -> None:
        self.word_list.clear()
        self.word_list.addItems(words)

    def set_banned_users(self, users: list[tuple[str, str]]) -> None:
        self.user_list.clear()
        for user_id, nickname in users:
            display = f"{user_id}" if not nickname else f"{user_id} ({nickname})"
            self.user_list.addItem(display)

    def add_word_to_list(self, word: str) -> None:
        self.word_list.addItem(word)

    def remove_word_from_list(self, word: str) -> None:
        items = self.word_list.findItems(word, Qt.MatchFlag.MatchExactly)
        for item in items:
            self.word_list.takeItem(self.word_list.row(item))
