from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from chzzk_tts.tts.base import VoiceSettings


class Database:
    def __init__(self, path: str = "chzzk_tts.db"):
        self._path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        with self._lock, self._conn:
            # Migration: add language column if missing (existing DB)
            existing = {
                row[1]
                for row in self._conn.execute(
                    "PRAGMA table_info(user_voice_settings)"
                ).fetchall()
            }
            if existing and "language" not in existing:
                self._conn.executescript("""
                    ALTER TABLE user_voice_settings RENAME TO user_voice_settings_old;
                    CREATE TABLE user_voice_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        nickname TEXT,
                        provider TEXT NOT NULL,
                        language TEXT NOT NULL DEFAULT 'ko-KR',
                        voice_id TEXT NOT NULL,
                        speed REAL NOT NULL DEFAULT 1.0,
                        pitch REAL NOT NULL DEFAULT 0.0,
                        extra_json TEXT DEFAULT '{}',
                        created_at TEXT DEFAULT (datetime('now')),
                        updated_at TEXT DEFAULT (datetime('now')),
                        UNIQUE(user_id, provider, language)
                    );
                    INSERT INTO user_voice_settings
                        (user_id, nickname, provider, language, voice_id, speed, pitch, extra_json, created_at, updated_at)
                    SELECT user_id, nickname, provider, 'ko-KR', voice_id, speed, pitch, extra_json, created_at, updated_at
                    FROM user_voice_settings_old;
                    DROP TABLE user_voice_settings_old;
                """)

            # Migration: recreate oauth_tokens table if using old schema
            oauth_cols = {
                row[1]
                for row in self._conn.execute(
                    "PRAGMA table_info(oauth_tokens)"
                ).fetchall()
            }
            if oauth_cols and "token_data" not in oauth_cols:
                # Old schema - drop and recreate
                self._conn.execute("DROP TABLE oauth_tokens")

            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS user_voice_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    nickname TEXT,
                    provider TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'ko-KR',
                    voice_id TEXT NOT NULL,
                    speed REAL NOT NULL DEFAULT 1.0,
                    pitch REAL NOT NULL DEFAULT 0.0,
                    extra_json TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(user_id, provider, language)
                );

                CREATE TABLE IF NOT EXISTS banned_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    nickname TEXT,
                    reason TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS banned_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL UNIQUE,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS oauth_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT NOT NULL UNIQUE,
                    token_data TEXT NOT NULL,  -- JSON serialized AccessToken
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
            """)

    # --- User voice settings ---

    def get_user_settings(
        self, user_id: str, provider: str, language: str = "ko-KR"
    ) -> VoiceSettings | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM user_voice_settings WHERE user_id = ? AND provider = ? AND language = ?",
                (user_id, provider, language),
            ).fetchone()
        if row is None:
            return None
        return VoiceSettings(
            provider_name=row["provider"],
            voice_id=row["voice_id"],
            speed=row["speed"],
            pitch=row["pitch"],
            extra=json.loads(row["extra_json"]),
        )

    def save_user_settings(
        self,
        user_id: str,
        nickname: str | None,
        settings: VoiceSettings,
        language: str = "ko-KR",
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO user_voice_settings (user_id, nickname, provider, language, voice_id, speed, pitch, extra_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, provider, language) DO UPDATE SET
                    nickname = excluded.nickname,
                    voice_id = excluded.voice_id,
                    speed = excluded.speed,
                    pitch = excluded.pitch,
                    extra_json = excluded.extra_json,
                    updated_at = datetime('now')
                """,
                (
                    user_id,
                    nickname,
                    settings.provider_name,
                    language,
                    settings.voice_id,
                    settings.speed,
                    settings.pitch,
                    json.dumps(settings.extra, ensure_ascii=False),
                ),
            )

    def get_all_users(self, provider: str | None = None) -> list[tuple[str, str]]:
        with self._lock:
            if provider:
                rows = self._conn.execute(
                    "SELECT DISTINCT user_id, nickname FROM user_voice_settings WHERE provider = ? ORDER BY user_id",
                    (provider,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT DISTINCT user_id, nickname FROM user_voice_settings ORDER BY user_id"
                ).fetchall()
        return [(r["user_id"], r["nickname"] or r["user_id"]) for r in rows]

    def remove_user_settings(self, user_id: str, provider: str | None = None) -> None:
        """Remove a user's voice settings from the database.

        Args:
            user_id: The user ID to remove
            provider: Optional provider name filter. If None, removes for all providers.
        """
        with self._lock, self._conn:
            if provider:
                self._conn.execute(
                    "DELETE FROM user_voice_settings WHERE user_id = ? AND provider = ?",
                    (user_id, provider),
                )
            else:
                self._conn.execute(
                    "DELETE FROM user_voice_settings WHERE user_id = ?",
                    (user_id,),
                )

    # --- Banned users ---

    def get_banned_users(self) -> list[tuple[str, str]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT user_id, nickname FROM banned_users ORDER BY user_id"
            ).fetchall()
        return [(r["user_id"], r["nickname"] or "") for r in rows]

    def add_banned_user(
        self, user_id: str, nickname: str = "", reason: str = ""
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO banned_users (user_id, nickname, reason) VALUES (?, ?, ?)",
                (user_id, nickname, reason),
            )

    def remove_banned_user(self, user_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))

    # --- Banned words ---

    def get_banned_words(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT word FROM banned_words ORDER BY word"
            ).fetchall()
        return [r["word"] for r in rows]

    def add_banned_word(self, word: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO banned_words (word) VALUES (?)", (word,)
            )

    def remove_banned_word(self, word: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM banned_words WHERE word = ?", (word,))

    # --- OAuth tokens ---

    def save_oauth_token(self, client_id: str, token_data: dict) -> None:
        """Save or update OAuth access token for the given client_id.

        Args:
            client_id: The OAuth client ID
            token_data: Dictionary containing AccessToken data (access_token, refresh_token, etc.)
        """
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO oauth_tokens (client_id, token_data)
                VALUES (?, ?)
                ON CONFLICT(client_id) DO UPDATE SET
                    token_data = excluded.token_data,
                    updated_at = datetime('now')
                """,
                (client_id, json.dumps(token_data, ensure_ascii=False)),
            )

    def get_oauth_token(self, client_id: str) -> dict | None:
        """Get stored OAuth token data for the given client_id.

        Returns:
            Dictionary with token data or None if not found
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT token_data FROM oauth_tokens WHERE client_id = ?",
                (client_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["token_data"])

    def clear_oauth_token(self, client_id: str) -> None:
        """Clear stored OAuth token for the given client_id."""
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM oauth_tokens WHERE client_id = ?",
                (client_id,),
            )

    def close(self) -> None:
        self._conn.close()
