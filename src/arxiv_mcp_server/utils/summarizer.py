"""LLM summarizer with multi-backend support."""
import os
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class Summarizer:
    """LLM-based paper summarizer with multi-backend support."""

    def __init__(self):
        self._anthropic_client = None
        self._openai_client = None

    def _get_anthropic_client(self):
        if self._anthropic_client is None:
            try:
                from anthropic import Anthropic
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not set")
                self._anthropic_client = Anthropic(api_key=api_key)
            except ImportError:
                raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        return self._anthropic_client

    async def summarize(
        self,
        text: str,
        model: str = "claude-sonnet-4-6",
        style: str = "technical",
    ) -> str:
        """Summarize text using LLM."""
        style_prompts = {
            "technical": self._technical_prompt,
            "beginner-friendly": self._beginner_friendly_prompt,
            "bullet-points": self._bullet_points_prompt,
        }

        prompt_template = style_prompts.get(style, self._technical_prompt)
        prompt = prompt_template(text)

        # Try Anthropic first
        try:
            client = self._get_anthropic_client()
            message = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.warning("anthropic_summarize_failed", error=str(e))
            raise

    @staticmethod
    def _technical_prompt(text: str) -> str:
        return f"""You are a research paper summarizer. Summarize the following paper in a technical style, focusing on:
1. Main contributions
2. Methodology
3. Experimental results
4. Limitations

Paper text:
{text}

Summary:"""

    @staticmethod
    def _beginner_friendly_prompt(text: str) -> str:
        return f"""You are a research paper summarizer. Summarize the following paper in an accessible way for someone new to the field:
1. What problem does it solve?
2. How does it solve it?
3. Why is this important?

Paper text:
{text}

Summary:"""

    @staticmethod
    def _bullet_points_prompt(text: str) -> str:
        return f"""You are a research paper summarizer. Summarize the following paper as 5-8 bullet points, each covering a key aspect.

Paper text:
{text}

Summary (bullet points):"""


# Global instance
_summarizer: Optional[Summarizer] = None


def get_summarizer() -> Summarizer:
    global _summarizer
    if _summarizer is None:
        _summarizer = Summarizer()
    return _summarizer