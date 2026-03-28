from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QStatusBar,
)

from chzzk_tts.ui.connection_panel import ConnectionPanel
from chzzk_tts.ui.tts_panel import TTSPanel
from chzzk_tts.ui.user_panel import UserPanel
from chzzk_tts.ui.filter_panel import FilterPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CHZZK Chat TTS")
        self.setMinimumSize(600, 500)
        self.resize(700, 550)

        # Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.connection_panel = ConnectionPanel()
        self.tts_panel = TTSPanel()
        self.user_panel = UserPanel()
        self.filter_panel = FilterPanel()

        self.tabs.addTab(self.connection_panel, "연결")
        self.tabs.addTab(self.tts_panel, "TTS 설정")
        self.tabs.addTab(self.user_panel, "사용자 음성")
        self.tabs.addTab(self.filter_panel, "필터")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("준비됨")
