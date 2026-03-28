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
from chzzkpy.authorization import AccessToken

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
    message_received = Signal(str, str, str)  # user_id, nickname, content
    login_status_changed = Signal(str)  # 로그인 단계 상태
    chat_status_changed = Signal(str)  # 채팅 연결 단계 상태
    token_saved = Signal(str)  # 토큰이 저장된 client_id

    def __init__(self, db=None, parent: QObject | None = None):
        super().__init__(parent)
        self._db = db
        self._client: Client | None = None
        self._user_client = None
        self._login_task: asyncio.Task | None = None
        self._chat_task: asyncio.Task | None = None
        self._current_client_id: str | None = None
        self._current_client_secret: str | None = None

    # ── 로그인 ────────────────────────────────────────────────────────────

    async def login(self, client_id: str, client_secret: str) -> None:
        await self._cancel_login_task()
        self._current_client_id = client_id
        self._current_client_secret = client_secret
        self.login_status_changed.emit("로그인 중...")
        self._login_task = asyncio.ensure_future(
            self._do_login(client_id, client_secret)
        )

    async def _do_login(self, client_id: str, client_secret: str) -> None:
        try:
            # First, try to use existing token
            if self._db:
                token_data = self._db.get_oauth_token(client_id)
                if token_data:
                    log.info("Found existing token, attempting auto-login...")
                    self.login_status_changed.emit("저장된 토큰으로 로그인 중...")
                    try:
                        self._client = Client(
                            client_id=client_id, client_secret=client_secret
                        )
                        await self._client._async_setup_hook()
                        # Reconstruct AccessToken from stored data
                        access_token = AccessToken(**token_data)
                        self._user_client = await self._client.get_user_client(
                            access_token
                        )
                        self.login_status_changed.emit("로그인됨")
                        log.info("Auto-login successful with stored token")
                        return
                    except Exception as e:
                        log.warning("Auto-login failed with stored token: %s", e)
                        self.login_status_changed.emit(
                            "저장된 토큰 만료, 재인증 필요..."
                        )

            # If no token or token failed, proceed with OAuth flow
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

            # Save token to database
            if self._db:
                # Serialize AccessToken to dict for storage (use by_alias=True to preserve camelCase field names)
                token_data = access_token.model_dump(by_alias=True)
                self._db.save_oauth_token(client_id, token_data)
                self.token_saved.emit(client_id)
                log.info("OAuth token saved to database")

            self.login_status_changed.emit("로그인됨")
        except asyncio.CancelledError:
            self.login_status_changed.emit("로그인 취소됨")
        except Exception as e:
            log.exception("CHZZK login error")
            self.login_status_changed.emit(f"로그인 실패: {e}")

    async def auto_login_with_token(self, client_id: str, client_secret: str) -> bool:
        """Try to login using stored token without showing OAuth dialog.

        Returns True if successful, False otherwise.
        """
        if not self._db:
            return False

        token_data = self._db.get_oauth_token(client_id)
        if not token_data:
            return False

        try:
            self.login_status_changed.emit("자동 로그인 중...")
            self._client = Client(client_id=client_id, client_secret=client_secret)
            await self._client._async_setup_hook()
            # Reconstruct AccessToken from stored data
            access_token = AccessToken(**token_data)
            self._user_client = await self._client.get_user_client(access_token)
            self._current_client_id = client_id
            self._current_client_secret = client_secret
            self.login_status_changed.emit("로그인됨")
            log.info("Auto-login successful")
            return True
        except Exception as e:
            log.warning("Auto-login failed: %s", e)
            self.login_status_changed.emit("자동 로그인 실패")
            return False

    async def cancel_login(self) -> None:
        if self._login_task and not self._login_task.done():
            await self._cancel_login_task()
            self.login_status_changed.emit("로그인 취소됨")

    async def logout(self, clear_token: bool = False) -> None:
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
            # Clear token if requested
            if clear_token and self._db and self._current_client_id:
                self._db.clear_oauth_token(self._current_client_id)
                log.info("OAuth token cleared from database")
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

    async def _validate_channel(self, channel_id: str) -> tuple[bool, str]:
        """Validate that the channel exists and is accessible."""
        try:
            # Attempt to fetch channel info to verify it exists
            # get_channel takes a list of channel IDs
            channels = await self._client.get_channel([channel_id])
            if not channels or channels[0] is None:
                return False, "채널을 찾을 수 없습니다. 채널 ID를 확인해주세요."
            return True, ""
        except Exception as e:
            log.warning("Channel validation failed: %s", e)
            return False, f"채널 확인 실패: {e}"

    async def connect_chat(self, channel_id: str) -> None:
        if not self._user_client:
            self.chat_status_changed.emit("연결 실패: 먼저 로그인하세요")
            return

        # Validate channel before attempting connection
        is_valid, error_msg = await self._validate_channel(channel_id)
        if not is_valid:
            self.chat_status_changed.emit(f"연결 실패: {error_msg}")
            return

        await self._cancel_chat_task()
        self.chat_status_changed.emit("채팅 연결 중...")
        self._chat_task = asyncio.ensure_future(self._do_connect_chat(channel_id))

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
