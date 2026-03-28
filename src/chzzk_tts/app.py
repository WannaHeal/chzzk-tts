from __future__ import annotations

import asyncio
import logging

from qasync import asyncSlot

from chzzk_tts.audio.player import AudioPlayer, PlaybackMode
from chzzk_tts.chat.client import ChzzkChatManager
from chzzk_tts.chat.filters import MessageFilter
from chzzk_tts.config import AppConfig
from chzzk_tts.db import Database
from chzzk_tts.tts.base import VoiceSettings, detect_language
from chzzk_tts.tts.edge_tts_provider import EdgeTTSProvider
from chzzk_tts.tts.engine import TTSEngine
from chzzk_tts.tts.google_tts import GoogleCloudTTSProvider
from chzzk_tts.ui.main_window import MainWindow
from chzzk_tts.ui.oauth_dialog import OAuthDialog

log = logging.getLogger(__name__)


def create_app() -> MainWindow:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = AppConfig.load()
    db = Database(config.db_path)

    # Core components
    audio_player = AudioPlayer()
    chat_manager = ChzzkChatManager()
    message_filter = MessageFilter(
        banned_words=db.get_banned_words(),
        banned_users=[u[0] for u in db.get_banned_users()],
        max_length=config.max_message_length,
        skip_commands=config.skip_commands,
    )
    tts_engine = TTSEngine(db=db, audio_player=audio_player)

    # Register TTS providers
    edge_provider = EdgeTTSProvider()
    tts_engine.register_provider(edge_provider)

    google_provider = GoogleCloudTTSProvider(config.google_credentials_path)
    tts_engine.register_provider(google_provider)

    tts_engine.set_provider(config.tts_provider)

    # GUI
    window = MainWindow()

    # --- Wire Connection Panel ---
    conn = window.connection_panel
    conn.load_config(config.client_id, config.client_secret, config.channel_id)

    # OAuth 인증 진행 다이얼로그 (재사용)
    oauth_dialog = OAuthDialog(window)

    @asyncSlot(str, str)
    async def on_login_requested(client_id: str, client_secret: str):
        config.client_id = client_id
        config.client_secret = client_secret
        config.save()
        await chat_manager.login(client_id, client_secret)
        oauth_dialog.show()

    conn.login_requested.connect(on_login_requested)

    # @asyncSlot() + Signal() (인수 없음) 조합은 qasync 버그로 동작하지 않음.
    # 인수 없는 async 슬롯은 일반 함수 + asyncio.ensure_future()로 우회.
    async def _do_logout():
        await chat_manager.logout()

    conn.logout_requested.connect(lambda: asyncio.ensure_future(_do_logout()))

    @asyncSlot(str)
    async def on_chat_connect_requested(channel_id: str):
        config.channel_id = channel_id
        config.save()
        await chat_manager.connect_chat(channel_id)

    conn.chat_connect_requested.connect(on_chat_connect_requested)

    async def _do_chat_disconnect():
        tts_engine.stop()
        await chat_manager.disconnect_chat()

    conn.chat_disconnect_requested.connect(lambda: asyncio.ensure_future(_do_chat_disconnect()))

    async def _do_cancel_login():
        await chat_manager.cancel_login()

    oauth_dialog.cancel_requested.connect(
        lambda: asyncio.ensure_future(_do_cancel_login())
    )

    def on_login_status(status: str):
        conn.set_login_status(status)
        window.status_bar.showMessage(status)
        oauth_dialog.on_status_changed(status)
        if status == "로그인됨":
            conn.set_login_state("logged_in")
        elif status in ("로그인 취소됨", "로그아웃됨") or "로그인 실패" in status:
            conn.set_login_state("logged_out")
            tts_engine.stop()
        else:  # "로그인 중..."
            conn.set_login_state("logging_in")

    chat_manager.login_status_changed.connect(on_login_status)

    def on_chat_status(status: str):
        conn.set_chat_status(status)
        window.status_bar.showMessage(status)
        if status == "연결됨":
            conn.set_chat_state("connected")
            tts_engine.start()
        elif status in ("연결 끊김",) or "연결 실패" in status:
            conn.set_chat_state("disconnected")
            tts_engine.stop()
        else:  # "채팅 연결 중..."
            conn.set_chat_state("connecting")

    chat_manager.chat_status_changed.connect(on_chat_status)

    # --- Wire Chat → TTS ---
    def on_message_received(user_id: str, nickname: str, content: str):
        conn.append_chat(nickname, content)
        content = MessageFilter.preprocess(content)
        if not message_filter.should_skip(user_id, content):
            tts_engine.enqueue(user_id, nickname, content)

    chat_manager.message_received.connect(on_message_received)

    # --- Wire TTS Panel ---
    tts_panel = window.tts_panel
    tts_panel.set_providers(tts_engine.provider_names)
    tts_panel.load_config(
        tts_enabled=config.tts_enabled,
        provider=config.tts_provider,
        playback_mode=config.playback_mode,
        volume_db=config.volume_db,
        max_length=config.max_message_length,
        skip_commands=config.skip_commands,
        google_cred_path=config.google_credentials_path,
        default_voice_ko=config.default_voice_ko,
        default_voice_ja=config.default_voice_ja,
        default_voice_en=config.default_voice_en,
    )

    def on_provider_changed(display_name: str):
        provider_name = tts_panel.current_provider_data()
        tts_engine.set_provider(provider_name)
        config.tts_provider = provider_name
        config.save()
        _refresh_default_voices()
        _refresh_user_panel_voices()

    tts_panel.provider_changed.connect(on_provider_changed)

    tts_panel.tts_enabled_changed.connect(lambda enabled: (
        tts_engine.set_enabled(enabled),
        setattr(config, "tts_enabled", enabled),
        config.save(),
    ))

    def on_playback_mode_changed(mode: str):
        audio_player.set_mode(
            PlaybackMode.INTERRUPT if mode == "interrupt" else PlaybackMode.SEQUENTIAL
        )
        config.playback_mode = mode
        config.save()

    tts_panel.playback_mode_changed.connect(on_playback_mode_changed)

    def on_volume_changed(db_val: float):
        audio_player.set_volume(db_val)
        config.volume_db = db_val
        config.save()

    tts_panel.volume_changed.connect(on_volume_changed)

    def on_max_length_changed(val: int):
        message_filter.max_length = val
        config.max_message_length = val
        config.save()

    tts_panel.max_length_changed.connect(on_max_length_changed)

    def on_skip_commands_changed(skip: bool):
        message_filter.skip_commands = skip
        config.skip_commands = skip
        config.save()

    tts_panel.skip_commands_changed.connect(on_skip_commands_changed)

    def on_google_cred_changed(path: str):
        google_provider.set_credentials(path)
        config.google_credentials_path = path
        config.save()

    tts_panel.google_credentials_changed.connect(on_google_cred_changed)

    def on_default_voice_changed(language: str, voice_id: str) -> None:
        tts_engine.set_default_voice(language, voice_id)
        if language == "ko-KR":
            config.default_voice_ko = voice_id
        elif language == "ja-JP":
            config.default_voice_ja = voice_id
        elif language == "en-US":
            config.default_voice_en = voice_id
        config.save()

    tts_panel.default_voice_changed.connect(on_default_voice_changed)

    tts_panel.clear_queue_requested.connect(lambda: (
        tts_engine.clear_queue(),
        audio_player.clear(),
    ))

    tts_engine.queue_size_changed.connect(tts_panel.set_queue_size)

    # --- Wire User Panel ---
    user_panel = window.user_panel

    def _refresh_default_voices():
        provider = tts_engine.active_provider
        if provider:
            tts_panel.set_default_voice_options(
                provider.get_available_voices("ko-KR"),
                provider.get_available_voices("ja-JP"),
                provider.get_available_voices("en-US"),
            )
            tts_panel.load_default_voices(
                config.default_voice_ko, config.default_voice_ja, config.default_voice_en
            )

    def _refresh_user_panel_voices():
        provider = tts_engine.active_provider
        if provider:
            language = user_panel.current_language()
            user_panel.set_voices(provider.get_available_voices(language), provider.name)

    def _refresh_user_list():
        provider = tts_engine.active_provider
        if provider:
            users = db.get_all_users(provider.name)
            user_panel.set_users(users)

    _refresh_default_voices()
    _refresh_user_panel_voices()
    _refresh_user_list()

    user_panel.refresh_btn.clicked.connect(_refresh_user_list)

    def on_user_selected():
        user_id = user_panel.user_combo.currentData()
        provider = tts_engine.active_provider
        if user_id and provider:
            language = user_panel.current_language()
            settings = db.get_user_settings(user_id, provider.name, language)
            if settings:
                user_panel.load_settings(settings)

    user_panel.user_combo.currentIndexChanged.connect(lambda _: on_user_selected())
    user_panel.language_changed.connect(lambda _: (_refresh_user_panel_voices(), on_user_selected()))

    def on_user_settings_updated(user_id: str, settings: VoiceSettings):
        language = user_panel.current_language()
        db.save_user_settings(user_id, None, settings, language)

    user_panel.settings_updated.connect(on_user_settings_updated)

    # --- Wire Filter Panel ---
    filter_panel = window.filter_panel
    filter_panel.set_banned_words(db.get_banned_words())
    filter_panel.set_banned_users(db.get_banned_users())

    def on_word_added(word: str):
        db.add_banned_word(word)
        message_filter.banned_words = db.get_banned_words()
        filter_panel.set_banned_words(db.get_banned_words())

    def on_word_removed(word: str):
        db.remove_banned_word(word)
        message_filter.banned_words = db.get_banned_words()
        filter_panel.set_banned_words(db.get_banned_words())

    def on_user_ban_added(user_id: str):
        db.add_banned_user(user_id)
        message_filter.banned_users = [u[0] for u in db.get_banned_users()]
        filter_panel.set_banned_users(db.get_banned_users())

    def on_user_ban_removed(display: str):
        user_id = display.split(" (")[0] if " (" in display else display
        db.remove_banned_user(user_id)
        message_filter.banned_users = [u[0] for u in db.get_banned_users()]
        filter_panel.set_banned_users(db.get_banned_users())

    filter_panel.banned_word_added.connect(on_word_added)
    filter_panel.banned_word_removed.connect(on_word_removed)
    filter_panel.banned_user_added.connect(on_user_ban_added)
    filter_panel.banned_user_removed.connect(on_user_ban_removed)

    # --- TTS Error handling ---
    tts_engine.tts_error.connect(
        lambda msg: window.status_bar.showMessage(f"TTS 오류: {msg}", 5000)
    )

    # Apply initial settings from config
    tts_engine.set_default_voice("ko-KR", config.default_voice_ko)
    tts_engine.set_default_voice("ja-JP", config.default_voice_ja)
    tts_engine.set_default_voice("en-US", config.default_voice_en)
    audio_player.set_volume(config.volume_db)
    audio_player.set_mode(
        PlaybackMode.INTERRUPT if config.playback_mode == "interrupt" else PlaybackMode.SEQUENTIAL
    )

    # Graceful shutdown
    def on_close():
        tts_engine.stop()
        audio_player.stop()
        db.close()

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app:
        app.aboutToQuit.connect(on_close)

    # 첫 실행 안내: Client ID가 설정되지 않은 경우 도움말 다이얼로그 자동 표시
    if not config.client_id:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(300, conn._on_help)

    return window
