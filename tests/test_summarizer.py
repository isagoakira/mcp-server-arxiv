"""Tests for summarizer.py."""

import pytest

from arxiv_mcp_server.utils.summarizer import Summarizer


class TestSummarizer:
    def test_raises_if_no_api_key(self, monkeypatch):
        """Test error when ANTHROPIC_API_KEY is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        summarizer = Summarizer()
        with pytest.raises((ValueError, RuntimeError)):
            summarizer._get_anthropic_client()

    def test_summarizer_singleton(self):
        """Test that get_summarizer returns singleton."""
        from arxiv_mcp_server.utils.summarizer import get_summarizer

        s1 = get_summarizer()
        s2 = get_summarizer()
        assert s1 is s2

    def test_technical_prompt_includes_text(self):
        """Test that technical prompt includes the paper text."""
        summarizer = Summarizer()
        prompt = summarizer._technical_prompt("paper content here")
        assert "paper content here" in prompt
        assert "Main contributions" in prompt
        assert "Methodology" in prompt

    def test_beginner_friendly_prompt(self):
        """Test that beginner-friendly prompt includes the paper text."""
        summarizer = Summarizer()
        prompt = summarizer._beginner_friendly_prompt("paper content here")
        assert "paper content here" in prompt
        assert "What problem does it solve" in prompt

    def test_bullet_points_prompt(self):
        """Test that bullet-points prompt includes the paper text."""
        summarizer = Summarizer()
        prompt = summarizer._bullet_points_prompt("paper content here")
        assert "paper content here" in prompt
        assert "bullet points" in prompt
