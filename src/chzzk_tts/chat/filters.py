from __future__ import annotations

import re


class MessageFilter:
    def __init__(
        self,
        banned_words: list[str] | None = None,
        banned_users: list[str] | None = None,
        max_length: int = 50,
        skip_commands: bool = True,
    ):
        self.banned_words: list[str] = banned_words or []
        self.banned_users: list[str] = banned_users or []
        self.max_length = max_length
        self.skip_commands = skip_commands

    def should_skip(self, user_id: str, content: str) -> bool:
        if not content:
            return True

        if user_id in self.banned_users:
            return True

        if self.skip_commands and content.startswith("!"):
            return True

        if len(content) > self.max_length:
            return True

        for word in self.banned_words:
            if word and word in content:
                return True

        return False

    @staticmethod
    def preprocess(content: str) -> str:
        # Replace URLs with "링크"
        content = re.sub(
            r"https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{2,256}\.[a-z]{2,4}\b([-a-zA-Z0-9@:%_+.~#?&/=]*)",
            "링크",
            content,
        )
        # Compress repeated characters
        content = re.sub(r"ㅋ{3,}", "ㅋㅋㅋ", content)
        content = re.sub(r"ㅎ{3,}", "ㅎㅎㅎ", content)
        content = re.sub(r"z{3,}", "zzz", content)
        content = re.sub(r"Z{3,}", "ZZZ", content)
        content = re.sub(r"@{4,}", "@@@@", content)
        content = re.sub(r"\?{3,}", "??", content)
        content = re.sub(r"!{3,}", "!!", content)
        content = re.sub(r"\.{4,}", "...", content)
        return content.strip()
