"""Integration tests for MCP server stdio protocol.

Run with: pytest tests/ -v -m integration
These tests are SKIPPED by default.
"""

import asyncio
import json
import sys

import pytest


async def start_server():
    """Start MCP server as subprocess."""
    venv_python = sys.executable

    proc = await asyncio.create_subprocess_exec(
        venv_python,
        "-m",
        "arxiv_mcp_server",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return proc


async def read_json_line(stream, timeout=10.0):
    """Read a line and try to parse as JSON, skipping non-JSON lines."""
    line = b""
    while True:
        chunk = await asyncio.wait_for(stream.read(1), timeout=timeout)
        if not chunk:
            raise RuntimeError("Stream closed")
        if chunk == b"\n":
            break
        line += chunk

    text = line.decode().strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Skip non-JSON output (logging, etc.)
        return None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_server_initialization():
    """Test that MCP server starts and responds to initialize."""
    proc = await start_server()
    try:
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0.1.0"},
            },
        }
        data = (json.dumps(request) + "\n").encode()
        proc.stdin.write(data)
        await proc.stdin.drain()

        # Read response (skip any non-JSON lines like structlog output)
        resp = None
        for _ in range(20):  # try up to 20 lines
            result = await read_json_line(proc.stdout, timeout=5.0)
            if result is not None and "result" in result:
                resp = result
                break

        assert resp is not None, "No JSON-RPC response received"
        assert "result" in resp

        # Send initialized notification
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        proc.stdin.write((json.dumps(notif) + "\n").encode())
        await proc.stdin.drain()

    finally:
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_server_starts_without_crash():
    """Test that server process doesn't crash on startup."""
    venv_python = sys.executable

    proc = await asyncio.create_subprocess_exec(
        venv_python,
        "-m",
        "arxiv_mcp_server",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Give server time to start
    await asyncio.sleep(1.0)

    # Wait and check if process is still running
    await asyncio.sleep(0.5)

    # Check if process has exited — if it exited with code 0, that's fine
    if proc.returncode is not None:
        assert proc.returncode == 0, f"Server process crashed with code {proc.returncode}"
        return

    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            pass
