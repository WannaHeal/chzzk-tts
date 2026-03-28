from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QLabel,
    QGroupBox,
    QMessageBox,
)


_HELP_TEXT = """\
<b>치지직 개발자 센터 앱 설정 안내</b><br><br>
<b>1. 필요한 API 권한 (scope)</b><br>
&nbsp;&nbsp;• <code>chat</code> — 채팅 메시지 수신<br><br>
<b>2. 등록해야 할 리다이렉트 URL</b><br>
&nbsp;&nbsp;<code>http://localhost:8080/</code><br><br>
위 리다이렉트 URL을 치지직 개발자 센터의 앱 설정에 정확히 추가해야<br>
OAuth 인증 후 자동으로 연결됩니다.
"""


class ConnectionPanel(QWidget):
    login_requested = Signal(str, str)  # client_id, client_secret
    logout_requested = Signal()  # logout but keep token
    logout_and_clear_requested = Signal()  # logout and clear token
    chat_connect_requested = Signal(str)  # channel_id
    chat_disconnect_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._logged_in = False
        self._chat_connected = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ── 로그인 그룹 ──────────────────────────────────────────────────
        login_group = QGroupBox("로그인")
        login_outer = QVBoxLayout()

        login_form = QFormLayout()
        self.client_id_edit = QLineEdit()
        self.client_id_edit.setPlaceholderText("Client ID")
        login_form.addRow("Client ID:", self.client_id_edit)

        self.client_secret_edit = QLineEdit()
        self.client_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_secret_edit.setPlaceholderText("Client Secret")
        login_form.addRow("Client Secret:", self.client_secret_edit)
        login_outer.addLayout(login_form)

        login_btn_row = QHBoxLayout()
        self.login_btn = QPushButton("로그인")
        self.login_status_label = QLabel("로그인 안 됨")
        self.help_btn = QPushButton("도움말")
        login_btn_row.addWidget(self.login_btn)
        login_btn_row.addWidget(self.login_status_label)
        login_btn_row.addStretch()
        login_btn_row.addWidget(self.help_btn)
        login_outer.addLayout(login_btn_row)

        login_group.setLayout(login_outer)
        layout.addWidget(login_group)

        # ── 채팅 연결 그룹 ───────────────────────────────────────────────
        chat_group = QGroupBox("채팅 연결")
        chat_outer = QVBoxLayout()

        chat_form = QFormLayout()
        self.channel_id_edit = QLineEdit()
        self.channel_id_edit.setPlaceholderText("채널 ID")
        chat_form.addRow("채널 ID:", self.channel_id_edit)
        chat_outer.addLayout(chat_form)

        chat_btn_row = QHBoxLayout()
        self.chat_connect_btn = QPushButton("채팅 연결")
        self.chat_connect_btn.setEnabled(False)
        self.chat_status_label = QLabel("연결 안 됨")
        chat_btn_row.addWidget(self.chat_connect_btn)
        chat_btn_row.addWidget(self.chat_status_label)
        chat_btn_row.addStretch()
        chat_outer.addLayout(chat_btn_row)

        chat_group.setLayout(chat_outer)
        layout.addWidget(chat_group)

        # ── 채팅 로그 ────────────────────────────────────────────────────
        log_group = QGroupBox("채팅 로그")
        log_layout = QVBoxLayout()
        self.chat_log = QPlainTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setMaximumBlockCount(500)
        log_layout.addWidget(self.chat_log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # ── 시그널 연결 ──────────────────────────────────────────────────
        self.login_btn.clicked.connect(self._on_login_toggle)
        self.login_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.login_btn.customContextMenuRequested.connect(self.show_logout_context_menu)
        self.chat_connect_btn.clicked.connect(self._on_chat_toggle)
        self.help_btn.clicked.connect(self._on_help)

    # ── 버튼 핸들러 ──────────────────────────────────────────────────────

    def _on_login_toggle(self) -> None:
        if self._logged_in:
            self.logout_requested.emit()
        else:
            self.login_requested.emit(
                self.client_id_edit.text().strip(),
                self.client_secret_edit.text().strip(),
            )

    def show_logout_context_menu(self, pos) -> None:
        """Show context menu for logout button to allow clearing token."""
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        logout_action = menu.addAction("로그아웃")
        logout_and_clear_action = menu.addAction("로그아웃 및 토큰 삭제")

        action = menu.exec(self.login_btn.mapToGlobal(pos))
        if action == logout_action:
            self.logout_requested.emit()
        elif action == logout_and_clear_action:
            self.logout_and_clear_requested.emit()

    def _on_chat_toggle(self) -> None:
        if self._chat_connected:
            self.chat_disconnect_requested.emit()
        else:
            self.chat_connect_requested.emit(self.channel_id_edit.text().strip())

    def _on_help(self) -> None:
        from PySide6.QtCore import Qt

        msg = QMessageBox(self)
        msg.setWindowTitle("앱 설정 안내")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(_HELP_TEXT)
        msg.open()

    # ── 상태 변경 메서드 ─────────────────────────────────────────────────

    def set_login_state(self, state: str) -> None:
        """state: 'logging_in' | 'logged_in' | 'logged_out'"""
        if state == "logging_in":
            self.login_btn.setEnabled(False)
            self.client_id_edit.setEnabled(False)
            self.client_secret_edit.setEnabled(False)
            self.chat_connect_btn.setEnabled(False)
        elif state == "logged_in":
            self._logged_in = True
            self.login_btn.setText("로그아웃")
            self.login_btn.setEnabled(True)
            self.client_id_edit.setEnabled(False)
            self.client_secret_edit.setEnabled(False)
            self.chat_connect_btn.setEnabled(True)
        elif state == "logged_out":
            self._logged_in = False
            self._chat_connected = False
            self.login_btn.setText("로그인")
            self.login_btn.setEnabled(True)
            self.client_id_edit.setEnabled(True)
            self.client_secret_edit.setEnabled(True)
            self.chat_connect_btn.setText("채팅 연결")
            self.chat_connect_btn.setEnabled(False)
            self.channel_id_edit.setEnabled(True)
            self.chat_status_label.setText("연결 안 됨")

    def set_chat_state(self, state: str) -> None:
        """state: 'connecting' | 'connected' | 'disconnected'"""
        if state == "connecting":
            self.chat_connect_btn.setEnabled(False)
            self.login_btn.setEnabled(False)
            self.channel_id_edit.setEnabled(False)
        elif state == "connected":
            self._chat_connected = True
            self.chat_connect_btn.setText("채팅 연결 끊기")
            self.chat_connect_btn.setEnabled(True)
            self.channel_id_edit.setEnabled(False)
            self.login_btn.setEnabled(False)  # 채팅 연결 중 로그아웃 비활성화
        elif state == "disconnected":
            self._chat_connected = False
            self.chat_connect_btn.setText("채팅 연결")
            self.chat_connect_btn.setEnabled(self._logged_in)
            self.channel_id_edit.setEnabled(True)
            self.login_btn.setEnabled(True)

    def set_login_status(self, status: str) -> None:
        self.login_status_label.setText(status)

    def set_chat_status(self, status: str) -> None:
        self.chat_status_label.setText(status)

    def append_chat(self, nickname: str, content: str) -> None:
        self.chat_log.appendPlainText(f"{nickname}: {content}")

    def load_config(self, client_id: str, client_secret: str, channel_id: str) -> None:
        self.client_id_edit.setText(client_id)
        self.client_secret_edit.setText(client_secret)
        self.channel_id_edit.setText(channel_id)
