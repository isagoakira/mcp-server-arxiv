"""Tests for rate_limiter.py."""

import asyncio
import time

import pytest

from arxiv_mcp_server.utils.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_enforces_interval():
    """Test that rate limiter enforces minimum interval."""
    limiter = RateLimiter(min_interval=0.1)

    start = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = time.monotonic() - start

    # Should have waited at least 0.1s between calls
    assert elapsed >= 0.09  # Allow small margin


@pytest.mark.asyncio
async def test_rate_limiter_allows_immediate_after_wait():
    """Test that rate limiter allows call after interval has passed."""
    limiter = RateLimiter(min_interval=0.05)

    await limiter.acquire()
    await asyncio.sleep(0.06)

    start = time.monotonic()
    await limiter.acquire()
    elapsed = time.monotonic() - start

    # Immediate call should not have waited much
    assert elapsed < 0.01
