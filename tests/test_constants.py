"""Unit tests for mdsync.constants module.

Tests constants used across mdsync modules.
"""

from mdsync.constants import SAFE_EMOJIS


class TestSafeEmojis:
    """Tests for SAFE_EMOJIS constant."""

    def test_safe_emojis_not_empty(self) -> None:
        """Test that SAFE_EMOJIS list is not empty."""
        assert len(SAFE_EMOJIS) > 0

    def test_safe_emojis_contains_only_strings(self) -> None:
        """Test that all elements in SAFE_EMOJIS are strings."""
        assert all(isinstance(emoji, str) for emoji in SAFE_EMOJIS)

    def test_safe_emojis_no_duplicates(self) -> None:
        """Test that SAFE_EMOJIS contains no duplicate emojis."""
        assert len(SAFE_EMOJIS) == len(set(SAFE_EMOJIS))

    def test_safe_emojis_no_empty_strings(self) -> None:
        """Test that SAFE_EMOJIS contains no empty strings."""
        assert all(len(emoji) > 0 for emoji in SAFE_EMOJIS)

    def test_safe_emojis_are_valid_unicode(self) -> None:
        """Test that all emojis are valid unicode characters."""
        for emoji in SAFE_EMOJIS:
            # Should not raise an exception
            emoji.encode("utf-8")

    def test_safe_emojis_contains_common_emojis(self) -> None:
        """Test that SAFE_EMOJIS contains some common emojis."""
        # Check for a few common emojis that should be present
        common_emojis = ["🐶", "🐱", "❤️", "⭐", "📚"]
        for emoji in common_emojis:
            assert emoji in SAFE_EMOJIS

    def test_safe_emojis_reasonable_size(self) -> None:
        """Test that SAFE_EMOJIS has a reasonable number of emojis."""
        # Should have at least 50 emojis, but not thousands
        assert 50 <= len(SAFE_EMOJIS) <= 1000
