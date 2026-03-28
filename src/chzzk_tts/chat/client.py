from __future__ import annotations

import asyncio
import logging
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from chzzkpy import Client, UserPermission

if TYPE_CHECKING:
    from chzzkpy import Message

log = logging.getLogger(__name__)

_REDIRECT_URL = "http://localhost:8080/"


class _OAuthCallbackServer:
    """스레드 기반 OAuth 콜백 서버.

    qasync + Windows IocpProactor 환경에서 aiohttp.web 서버를 시작하면
    accept_coro Task 컨텍스트 충돌이 발생합니다. 이를 완전히 우회하기 위해
    내장 http.server를 별도 데몬 스레드에서 실행하고,
    asyncio와의 통신은 run_in_executor + threading.Event로 처리합니다.
    """

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self._server: HTTPServer | None = None
        self._done_event = threading.Event()
        self._result: dict | None = None

    async def wait_for_callback(self) -> dict:
        """브라우저 콜백을 기다립니다. {'code': str, 'state': str}을 반환합니다."""
        handler_cls = self._make_handler()
        self._server = HTTPServer((self.host, self.port), handler_cls)

        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()

        loop = asyncio.get_running_loop()
        try:
            # run_in_executor로 스레드에서 이벤트를 기다림 (asyncio 루프 블로킹 없음)
            await loop.run_in_executor(None, self._done_event.wait)
        except asyncio.CancelledError:
            # 취소 시 blocking 중인 executor 스레드를 깨움
            self._done_event.set()
            raise
        finally:
            self._shutdown()

        if self._result is None:
            raise asyncio.CancelledError
        return self._result

    def _make_handler(self):
        server_ref = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                code = params.get("code", [None])[0]
                state = params.get("state", [None])[0]

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    "<html><body><h2>인증 성공! 이 창을 닫아도 됩니다.</h2></body></html>".encode()
                )

                server_ref._result = {"code": code, "state": state}
                server_ref._done_event.set()

            def log_message(self, format, *args):  # noqa: A002
                pass  # HTTP 접근 로그 억제

        return _Handler

    def _shutdown(self):
        if self._server:
            # shutdown()은 블로킹이므로 별도 스레드에서 실행
            threading.Thread(target=self._server.shutdown, daemon=True).start()
            self._server = None


class ChzzkChatManager(QObject):
    message_received = Signal(str, str, str)   # user_id, nickname, content
    login_status_changed = Signal(str)          # 로그인 단계 상태
    chat_status_changed = Signal(str)           # 채팅 연결 단계 상태

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._client: Client | None = None
        self._user_client = None
        self._login_task: asyncio.Task | None = None
        self._chat_task: asyncio.Task | None = None

    # ── 로그인 ────────────────────────────────────────────────────────────

    async def login(self, client_id: str, client_secret: str) -> None:
        await self._cancel_login_task()
        self.login_status_changed.emit("로그인 중...")
        self._login_task = asyncio.ensure_future(
            self._do_login(client_id, client_secret)
        )

    async def _do_login(self, client_id: str, client_secret: str) -> None:
        try:
            self._client = Client(client_id=client_id, client_secret=client_secret)
            await self._client._async_setup_hook()

            state = secrets.token_hex(8)
            auth_url = self._client.generate_authorization_token_url(
                redirect_url=_REDIRECT_URL, state=state
            )
            log.info("OAuth URL: %s", auth_url)
            webbrowser.open(auth_url)

            oauth_server = _OAuthCallbackServer()
            result = await oauth_server.wait_for_callback()

            if result["code"] is None or result["state"] != state:
                raise ValueError(f"OAuth 인증 실패: 잘못된 응답 ({result})")

            access_token = await self._client.generate_access_token(
                result["code"], state=state
            )
            self._user_client = await self._client.get_user_client(access_token)
            self.login_status_changed.emit("로그인됨")
        except asyncio.CancelledError:
            self.login_status_changed.emit("로그인 취소됨")
        except Exception as e:
            log.exception("CHZZK login error")
            self.login_status_changed.emit(f"로그인 실패: {e}")

    async def cancel_login(self) -> None:
        if self._login_task and not self._login_task.done():
            await self._cancel_login_task()
            self.login_status_changed.emit("로그인 취소됨")

    async def logout(self) -> None:
        await self._cancel_login_task()
        await self._cancel_chat_task()
        # 채팅 연결이 있었으면 상태 초기화
        if self._user_client is not None:
            self.chat_status_changed.emit("연결 끊김")
        try:
            if self._client:
                await self._client.close()
        except Exception:
            log.exception("CHZZK logout error")
        finally:
            self._client = None
            self._user_client = None
        self.login_status_changed.emit("로그아웃됨")

    async def _cancel_login_task(self) -> None:
        if self._login_task and not self._login_task.done():
            self._login_task.cancel()
            try:
                await self._login_task
            except (asyncio.CancelledError, Exception):
                pass
        self._login_task = None

    # ── 채팅 연결 ─────────────────────────────────────────────────────────

    async def connect_chat(self, channel_id: str) -> None:
        if not self._user_client:
            self.chat_status_changed.emit("연결 실패: 먼저 로그인하세요")
            return
        await self._cancel_chat_task()
        self.chat_status_changed.emit("채팅 연결 중...")
        self._chat_task = asyncio.ensure_future(
            self._do_connect_chat(channel_id)
        )

    async def _do_connect_chat(self, channel_id: str) -> None:  # noqa: ARG002
        try:
            manager = self

            @self._client.event
            async def on_connect(*args):
                manager.chat_status_changed.emit("연결됨")

            @self._client.event
            async def on_chat(message: Message):
                user_id = message.user_id or ""
                nickname = message.profile.nickname if message.profile else ""
                content = message.content or ""
                manager.message_received.emit(user_id, nickname, content)

            await self._user_client.connect(
                permission=UserPermission(chat=True, donation=False)
            )
            # connect()가 정상 반환 = 연결 종료 (서버 측 닫힘 등)
            self.chat_status_changed.emit("연결 끊김")
        except asyncio.CancelledError:
            raise  # disconnect_chat()에서 "연결 끊김" emit
        except Exception as e:
            log.exception("CHZZK chat connection error")
            self.chat_status_changed.emit(f"연결 실패: {e}")

    async def disconnect_chat(self) -> None:
        await self._cancel_chat_task()
        self.chat_status_changed.emit("연결 끊김")

    async def _cancel_chat_task(self) -> None:
        if self._chat_task and not self._chat_task.done():
            self._chat_task.cancel()
            try:
                await self._chat_task
            except (asyncio.CancelledError, Exception):
                pass
        self._chat_task = None

    # ── 속성 ──────────────────────────────────────────────────────────────

    @property
    def is_logged_in(self) -> bool:
        return self._user_client is not None

    @property
    def is_chat_connected(self) -> bool:
        return self._chat_task is not None and not self._chat_task.done()
