"""Tests for the chat message filtering and preprocessing functionality."""

from __future__ import annotations

import pytest

from chzzk_tts.chat.filters import MessageFilter


class TestMessageFilterPreprocess:
    """Test cases for the preprocess method."""

    def test_url_replacement(self):
        """Test that URLs are replaced with '링크'."""
        assert (
            MessageFilter.preprocess("Check out https://example.com")
            == "Check out 링크"
        )
        assert MessageFilter.preprocess("Visit http://test.co.kr/path") == "Visit 링크"
        assert (
            MessageFilter.preprocess("https://www.google.com/search?q=test") == "링크"
        )

    def test_jaum_conversion_single_characters(self):
        """Test conversion of single Korean Jaum characters."""
        # Basic consonants
        assert MessageFilter.preprocess("ㄱ") == "기역"
        assert MessageFilter.preprocess("ㄴ") == "니은"
        assert MessageFilter.preprocess("ㄷ") == "디귿"
        assert MessageFilter.preprocess("ㄹ") == "리을"
        assert MessageFilter.preprocess("ㅁ") == "미음"
        assert MessageFilter.preprocess("ㅂ") == "비읍"
        assert MessageFilter.preprocess("ㅅ") == "시옷"
        assert MessageFilter.preprocess("ㅇ") == "이응"
        assert MessageFilter.preprocess("ㅈ") == "지읒"
        assert MessageFilter.preprocess("ㅊ") == "치읓"
        assert MessageFilter.preprocess("ㅋ") == "키읔"
        assert MessageFilter.preprocess("ㅌ") == "티읕"
        assert MessageFilter.preprocess("ㅍ") == "피읖"
        assert MessageFilter.preprocess("ㅎ") == "히읗"

    def test_jaum_conversion_double_consonants(self):
        """Test conversion of double Korean Jaum characters."""
        assert MessageFilter.preprocess("ㄲ") == "쌍기역"
        assert MessageFilter.preprocess("ㄸ") == "쌍디귿"
        assert MessageFilter.preprocess("ㅃ") == "쌍비읍"
        assert MessageFilter.preprocess("ㅆ") == "쌍시옷"
        assert MessageFilter.preprocess("ㅉ") == "쌍지읒"

    def test_moum_conversion_single_vowels(self):
        """Test conversion of single Korean Moum (vowel) characters."""
        assert MessageFilter.preprocess("ㅏ") == "아"
        assert MessageFilter.preprocess("ㅑ") == "야"
        assert MessageFilter.preprocess("ㅓ") == "어"
        assert MessageFilter.preprocess("ㅕ") == "여"
        assert MessageFilter.preprocess("ㅗ") == "오"
        assert MessageFilter.preprocess("ㅛ") == "요"
        assert MessageFilter.preprocess("ㅜ") == "우"
        assert MessageFilter.preprocess("ㅠ") == "유"
        assert MessageFilter.preprocess("ㅡ") == "으"
        assert MessageFilter.preprocess("ㅣ") == "이"

    def test_moum_conversion_compound_vowels(self):
        """Test conversion of compound Korean Moum characters."""
        assert MessageFilter.preprocess("ㅐ") == "애"
        assert MessageFilter.preprocess("ㅒ") == "얘"
        assert MessageFilter.preprocess("ㅔ") == "에"
        assert MessageFilter.preprocess("ㅖ") == "예"
        assert MessageFilter.preprocess("ㅘ") == "와"
        assert MessageFilter.preprocess("ㅙ") == "왜"
        assert MessageFilter.preprocess("ㅚ") == "외"
        assert MessageFilter.preprocess("ㅝ") == "워"
        assert MessageFilter.preprocess("ㅞ") == "웨"
        assert MessageFilter.preprocess("ㅟ") == "위"
        assert MessageFilter.preprocess("ㅢ") == "의"

    def test_jaum_in_sentence(self):
        """Test Jaum conversion within sentences."""
        assert MessageFilter.preprocess("ㄱㄱ") == "기역기역"
        assert MessageFilter.preprocess("ㄴㅇ") == "니은이응"
        assert MessageFilter.preprocess("Hello ㄱ world") == "Hello 기역 world"

    def test_moum_in_sentence(self):
        """Test Moum conversion within sentences."""
        assert MessageFilter.preprocess("ㅏㅏ") == "아아"
        assert MessageFilter.preprocess("ㅗㅜㅏ") == "오우아"
        assert MessageFilter.preprocess("Hello ㅏ world") == "Hello 아 world"

    def test_mixed_korean_in_sentence(self):
        """Test mixed Jaum and Moum conversion."""
        assert MessageFilter.preprocess("ㄱㅏ") == "기역아"
        assert MessageFilter.preprocess("ㄴㅣㅇㅡㄴ") == "니은이이응으니은"

    def test_repeated_character_compaction_6_or_more(self):
        """Test that characters repeated 6+ times are compacted to 5."""
        # English characters - single character repetition
        assert MessageFilter.preprocess("aaaaaa") == "aaaaa"
        assert MessageFilter.preprocess("bbbbbbbbbb") == "bbbbb"

        # Numbers
        assert MessageFilter.preprocess("1111111") == "11111"

        # Korean text (not Jaum/Moum, which get converted to longer strings)
        assert MessageFilter.preprocess("하하하하하하하하") == "하하하하하"

    def test_repeated_character_no_compaction_below_6(self):
        """Test that characters repeated less than 6 times are not compacted by the generic rule."""
        # These should remain unchanged by the generic compaction rule
        assert MessageFilter.preprocess("aaaaa") == "aaaaa"
        assert MessageFilter.preprocess("하하하") == "하하하"
        # Note: ㅋㅋㅋ gets converted to 키읔키읔키읔 (see test_korean_laughter_compression_kkk)

    def test_korean_laughter_compression_kkk(self):
        """Test that ㅋㅋㅋㅋㅋ is compressed to ㅋㅋㅋ, then converted to 키읔키읔키읔."""
        assert MessageFilter.preprocess("ㅋㅋㅋㅋㅋ") == "키읔키읔키읔"
        assert (
            MessageFilter.preprocess("ㅋㅋㅋㅋㅋㅋ") == "키읔키읔키읔"
        )  # Compacted to 3 first, then converted
        assert (
            MessageFilter.preprocess("ㅋㅋㅋ") == "키읔키읔키읔"
        )  # Converted directly

    def test_korean_laughter_compression_hhh(self):
        """Test that ㅎㅎㅎㅎ is compressed to ㅎㅎㅎ, then converted to 히읗히읗히읗."""
        assert MessageFilter.preprocess("ㅎㅎㅎㅎ") == "히읗히읗히읗"

    def test_z_compression(self):
        """Test that zzz pattern is preserved."""
        assert MessageFilter.preprocess("zzzz") == "zzz"
        assert MessageFilter.preprocess("zzzzz") == "zzz"

    def test_question_mark_compression(self):
        """Test that ??? pattern is preserved."""
        assert MessageFilter.preprocess("????") == "??"
        assert MessageFilter.preprocess("?????") == "??"

    def test_exclamation_compression(self):
        """Test that !!! pattern is preserved."""
        assert MessageFilter.preprocess("!!!!") == "!!"
        assert MessageFilter.preprocess("!!!!!") == "!!"

    def test_dot_compression(self):
        """Test that .... pattern is preserved."""
        assert MessageFilter.preprocess(".....") == "..."
        assert MessageFilter.preprocess("......") == "..."

    def test_at_symbol_compression(self):
        """Test that @@@@ pattern is preserved."""
        assert MessageFilter.preprocess("@@@@@") == "@@@@"
        assert MessageFilter.preprocess("@@@@@@") == "@@@@"

    def test_whitespace_stripping(self):
        """Test that leading/trailing whitespace is stripped."""
        assert MessageFilter.preprocess("  hello  ") == "hello"
        assert MessageFilter.preprocess("\t\ttest\n") == "test"

    def test_complex_combination(self):
        """Test complex combinations of multiple transformations."""
        # Mixed Jaum, Moum, URL, and repeated chars
        # ㅋㅋㅋㅋㅋ (5 times) -> compressed to ㅋㅋㅋ -> converted to 키읔키읔키읔
        result = MessageFilter.preprocess("https://test.com ㄱㅏㅋㅋㅋㅋㅋㅋㅋㅋㅋ")
        assert result == "링크 기역아키읔키읔키읔"

    def test_empty_string(self):
        """Test empty string handling."""
        assert MessageFilter.preprocess("") == ""

    def test_no_korean_characters(self):
        """Test that non-Korean text is not affected."""
        assert MessageFilter.preprocess("Hello World") == "Hello World"
        assert MessageFilter.preprocess("12345 test") == "12345 test"


class TestMessageFilterShouldSkip:
    """Test cases for the should_skip method."""

    def test_empty_content(self):
        """Test that empty content is skipped."""
        filter_obj = MessageFilter()
        assert filter_obj.should_skip("user123", "") is True

    def test_banned_user(self):
        """Test that banned users are skipped."""
        filter_obj = MessageFilter(banned_users=["baduser", "spammer"])
        assert filter_obj.should_skip("baduser", "Hello") is True
        assert filter_obj.should_skip("spammer", "Test") is True
        assert filter_obj.should_skip("gooduser", "Hello") is False

    def test_commands_skipped(self):
        """Test that commands (starting with !) are skipped."""
        filter_obj = MessageFilter(skip_commands=True)
        assert filter_obj.should_skip("user", "!help") is True
        assert filter_obj.should_skip("user", "!play song") is True
        assert filter_obj.should_skip("user", "Hello!") is False
        assert filter_obj.should_skip("user", "Not a command") is False

    def test_commands_not_skipped(self):
        """Test that commands are not skipped when disabled."""
        filter_obj = MessageFilter(skip_commands=False)
        assert filter_obj.should_skip("user", "!help") is False

    def test_max_length(self):
        """Test that messages exceeding max length are skipped."""
        filter_obj = MessageFilter(max_length=10)
        assert filter_obj.should_skip("user", "Short") is False
        assert filter_obj.should_skip("user", "This is a very long message") is True

    def test_banned_words(self):
        """Test that messages with banned words are skipped."""
        filter_obj = MessageFilter(banned_words=["spam", "badword"])
        assert filter_obj.should_skip("user", "This is spam") is True
        assert filter_obj.should_skip("user", "badword here") is True
        assert filter_obj.should_skip("user", "This is good") is False

    def test_banned_word_partial_match(self):
        """Test that banned words match as substrings."""
        filter_obj = MessageFilter(banned_words=["bad"])
        assert filter_obj.should_skip("user", "badword") is True
        assert filter_obj.should_skip("user", "This is bad") is True
        assert filter_obj.should_skip("user", "good") is False


class TestMessageFilterInitialization:
    """Test cases for MessageFilter initialization."""

    def test_default_initialization(self):
        """Test default initialization parameters."""
        filter_obj = MessageFilter()
        assert filter_obj.banned_words == []
        assert filter_obj.banned_users == []
        assert filter_obj.max_length == 50
        assert filter_obj.skip_commands is True

    def test_custom_initialization(self):
        """Test custom initialization parameters."""
        filter_obj = MessageFilter(
            banned_words=["word1"],
            banned_users=["user1"],
            max_length=100,
            skip_commands=False,
        )
        assert filter_obj.banned_words == ["word1"]
        assert filter_obj.banned_users == ["user1"]
        assert filter_obj.max_length == 100
        assert filter_obj.skip_commands is False

    def test_none_initialization(self):
        """Test that None values are converted to empty lists."""
        filter_obj = MessageFilter(banned_words=None, banned_users=None)
        assert filter_obj.banned_words == []
        assert filter_obj.banned_users == []
