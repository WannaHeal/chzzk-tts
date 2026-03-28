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

        # Keep existing specific character compressions for 3+ repetitions
        # These must be done BEFORE Jaum/Moum conversion
        content = re.sub(r"ㅋ{3,}", "ㅋㅋㅋ", content)
        content = re.sub(r"ㅎ{3,}", "ㅎㅎㅎ", content)
        content = re.sub(r"z{3,}", "zzz", content)
        content = re.sub(r"Z{3,}", "ZZZ", content)
        content = re.sub(r"@{4,}", "@@@@", content)
        content = re.sub(r"\?{3,}", "??", content)
        content = re.sub(r"!{3,}", "!!", content)
        content = re.sub(r"\.{4,}", "...", content)

        # Compact any character repeated 6+ times to 5 repetitions
        # This must be done BEFORE Jaum/Moum conversion
        def compact_repeated(match: re.Match) -> str:
            char = match.group(1)
            return char * 5

        content = re.sub(r"(.)\1{5,}", compact_repeated, content)

        # Convert Korean Jaum (consonants) to full letter names
        jaum_map = {
            "ㄱ": "기역",
            "ㄲ": "쌍기역",
            "ㄴ": "니은",
            "ㄷ": "디귿",
            "ㄸ": "쌍디귿",
            "ㄹ": "리을",
            "ㅁ": "미음",
            "ㅂ": "비읍",
            "ㅃ": "쌍비읍",
            "ㅅ": "시옷",
            "ㅆ": "쌍시옷",
            "ㅇ": "이응",
            "ㅈ": "지읒",
            "ㅉ": "쌍지읒",
            "ㅊ": "치읓",
            "ㅋ": "키읔",
            "ㅌ": "티읕",
            "ㅍ": "피읖",
            "ㅎ": "히읗",
        }
        for jaum, full_name in jaum_map.items():
            content = content.replace(jaum, full_name)

        # Convert Korean Moum (vowels) to full letters with ㅇ
        moum_map = {
            "ㅏ": "아",
            "ㅐ": "애",
            "ㅑ": "야",
            "ㅒ": "얘",
            "ㅓ": "어",
            "ㅔ": "에",
            "ㅕ": "여",
            "ㅖ": "예",
            "ㅗ": "오",
            "ㅘ": "와",
            "ㅙ": "왜",
            "ㅚ": "외",
            "ㅛ": "요",
            "ㅜ": "우",
            "ㅝ": "워",
            "ㅞ": "웨",
            "ㅟ": "위",
            "ㅠ": "유",
            "ㅡ": "으",
            "ㅢ": "의",
            "ㅣ": "이",
        }
        for moum, full_name in moum_map.items():
            content = content.replace(moum, full_name)

        return content.strip()
