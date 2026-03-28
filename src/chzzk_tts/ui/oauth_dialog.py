from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)


class OAuthDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("치지직 인증")
        self.setFixedSize(380, 130)
        # 닫기(X) 버튼 비활성화 — 취소 버튼만으로 종료
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        label = QLabel(
            "브라우저에서 치지직 로그인을 진행해 주세요.\n"
            "인증이 완료되면 자동으로 연결됩니다."
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton("취소")
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def showEvent(self, event):
        """다이얼로그가 표시될 때마다 버튼 상태를 초기화합니다."""
        super().showEvent(event)
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setText("취소")

    def _on_cancel(self):
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText("취소 중...")
        self.cancel_requested.emit()

    def on_status_changed(self, status: str) -> None:
        """login_status_changed 시그널에 연결해 상태에 따라 다이얼로그를 닫습니다."""
        if not self.isVisible():
            return
        if status == "로그인됨":
            self.accept()
        elif "로그인 실패" in status or status == "로그인 취소됨":
            self.reject()
