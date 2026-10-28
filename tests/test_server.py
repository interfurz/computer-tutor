import asyncio
import base64
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp.exceptions import ToolError

from computer_tutor.models import TutorState
from computer_tutor.server import create_server


class ImmediateBridge:
    def call(self, function):
        return function()


@asynccontextmanager
async def connected_client():
    executable = os.environ.get("COMPUTER_TUTOR_TEST_EXE")
    parameters = StdioServerParameters(
        command=executable or sys.executable,
        args=(
            ["--mcp"] if executable else ["-m", "computer_tutor", "--mcp", "--allow-non-windows"]
        ),
        env={"QT_QPA_PLATFORM": "offscreen"},
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def test_real_stdio_client_can_teach_and_navigate_without_input_permission():
    async def scenario():
        async with connected_client() as session:
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert "tutor_capture_screen" in names
            assert "desktop_click" in names
            assert not any("permission" in name or "enable_control" in name for name in names)
            monitors = await session.call_tool("tutor_list_monitors", {})
            assert not monitors.isError
            monitor_id = monitors.structuredContent["result"][0]["id"]
            tutorial = {
                "title": "Integration",
                "monitor_id": monitor_id,
                "steps": [
                    {"title": "Start", "explanation": "Öffne dein Programm."},
                    {"title": "Ende", "explanation": "Prüfe das Ergebnis."},
                ],
            }
            loaded = await session.call_tool("tutor_present_tutorial", {"tutorial": tutorial})
            assert not loaded.isError
            assert loaded.structuredContent["step_index"] == 0
            moved = await session.call_tool("tutor_navigate", {"direction": "next"})
            assert moved.structuredContent["step"]["title"] == "Ende"
            updated = await session.call_tool(
                "tutor_update_step",
                {
                    "step": {
                        "title": "Aktualisiert",
                        "explanation": "Der Bildschirm hat sich geändert.",
                    }
                },
            )
            assert updated.structuredContent["step_index"] == 1
            assert updated.structuredContent["step"]["title"] == "Aktualisiert"
            blocked = await session.call_tool("desktop_type_text", {"text": "Never injected"})
            assert blocked.isError
            invalid = await session.call_tool(
                "desktop_click",
                {
                    "monitor_id": monitor_id,
                    "x": 1.5,
                    "y": 0.1,
                },
            )
            assert invalid.isError
            stopped = await session.call_tool("tutor_stop", {})
            assert not stopped.structuredContent["annotations_visible"]
            assert not stopped.structuredContent["control_enabled"]

    asyncio.run(scenario())


def test_eof_closes_the_hud_process():
    process = subprocess.run(
        [sys.executable, "-m", "computer_tutor", "--mcp", "--allow-non-windows"],
        input="",
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == ""


def test_screenshot_failure_still_restores_hud(monkeypatch):
    controller = Mock()
    controller.state = TutorState()
    controller.begin_capture.return_value = {
        "physical_bounds": {
            "left": 0,
            "top": 0,
            "width": 1920,
            "height": 1080,
        }
    }
    server = create_server(ImmediateBridge(), controller)
    monkeypatch.setattr("computer_tutor.server.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(
        "computer_tutor.server.mss.mss", Mock(side_effect=OSError("capture failed"))
    )
    with pytest.raises(ToolError, match="capture failed"):
        asyncio.run(server._tool_manager.call_tool("tutor_capture_screen", {"monitor_id": "test"}))
    controller.end_capture.assert_called_once()


def test_screenshot_returns_pixels_and_monitor_metadata(monkeypatch):
    controller = Mock()
    controller.state = TutorState()
    monitor = {"physical_bounds": {"left": -2, "top": 0, "width": 2, "height": 2}}
    controller.begin_capture.return_value = monitor
    controller.monitor.return_value = monitor
    shot = Mock(rgb=b"\xff\x00\x00" * 4, size=(2, 2), width=2, height=2)
    capture = Mock()
    capture.__enter__ = Mock(return_value=capture)
    capture.__exit__ = Mock(return_value=False)
    capture.grab.return_value = shot
    monkeypatch.setattr("computer_tutor.server.mss.mss", Mock(return_value=capture))
    monkeypatch.setattr("computer_tutor.server.time.sleep", lambda _seconds: None)
    server = create_server(ImmediateBridge(), controller)
    result = asyncio.run(
        server._tool_manager.call_tool(
            "tutor_capture_screen",
            {"monitor_id": "test"},
        )
    )
    assert result[0].type == "text"
    assert result[1].mimeType == "image/png"
    assert base64.b64decode(result[1].data).startswith(b"\x89PNG")
    controller.end_capture.assert_called_once()
