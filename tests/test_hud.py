import sys
from concurrent.futures import Future
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from computer_tutor.bridge import GuiBridge
from computer_tutor.controller import TutorController
from computer_tutor.demo import demo_tutorial
from computer_tutor.models import TutorState


@pytest.fixture(scope="module")
def hud(qt_app):
    app = qt_app
    controller = TutorController(app)
    yield app, controller
    controller.hotkey.close()
    app.removeNativeEventFilter(controller.hotkey)
    controller.overlay.close()
    controller.dock.close()


@pytest.fixture(autouse=True)
def reset(hud, monkeypatch):
    app, controller = hud
    controller.state = TutorState()
    controller.input_backend = Mock()
    controller.capture_depth = 0
    screen = app.primaryScreen()
    geometry = screen.geometry()
    monkeypatch.setattr(
        "computer_tutor.controller.physical_monitors",
        lambda: {
            screen.name(): (geometry.x(), geometry.y(), geometry.width(), geometry.height()),
        },
    )
    controller.load(demo_tutorial(controller.id_for(screen)))
    app.processEvents()


def test_click_through_layer_and_navigation(hud):
    app, controller = hud
    assert controller.overlay.windowFlags() & Qt.WindowType.WindowTransparentForInput
    assert controller.dock.counter.text() == "1 / 3"
    assert not controller.dock.previous.isEnabled()
    QTest.mouseClick(controller.dock.next, Qt.MouseButton.LeftButton)
    app.processEvents()
    assert controller.dock.counter.text() == "2 / 3"
    assert controller.state.step.annotations[0].style == "spotlight"
    controller.input_backend.click.assert_not_called()
    # Exercise the actual painter, including spotlight/card layout, in offscreen Qt.
    assert not controller.overlay.grab().isNull()
    QTest.mouseClick(controller.dock.previous, Qt.MouseButton.LeftButton)
    assert controller.state.step_index == 0


def test_agent_text_is_plaintext(hud):
    _, controller = hud
    step = controller.state.step.model_copy(
        update={
            "title": "<b>Literal title</b>",
            "explanation": "<script>literal text</script>",
        }
    )
    controller.replace_step(step)
    assert controller.dock.title.textFormat() == Qt.TextFormat.PlainText
    assert controller.dock.explanation.toPlainText() == "<script>literal text</script>"


@pytest.mark.parametrize(
    "action, arguments",
    [
        ("click", {"monitor_id": "unknown", "x": 0.1, "y": 0.1, "button": "left"}),
        ("type_text", {"text": "Grüße 👋"}),
        ("hotkey", {"keys": ["ctrl", "s"]}),
        ("scroll", {"ticks": 1}),
    ],
)
def test_every_input_checks_local_permission_first(hud, action, arguments):
    _, controller = hud
    with pytest.raises(PermissionError):
        controller.desktop_action(action, **arguments)
    assert not controller.input_backend.mock_calls


def test_agent_cannot_click_its_permission_switch(hud):
    app, controller = hud
    controller.state.control_enabled = True
    screen = app.primaryScreen()
    center = controller.dock.geometry().center()
    area = screen.geometry()
    x = (center.x() - area.x()) / (area.width() - 1)
    y = (center.y() - area.y()) / (area.height() - 1)
    with pytest.raises(ValueError, match="own controls"):
        controller.desktop_action(
            "click", monitor_id=controller.id_for(screen), x=x, y=y, button="left"
        )
    controller.input_backend.click.assert_not_called()


def test_stop_button_revokes_permission(hud):
    _, controller = hud
    controller.state.control_enabled = True
    controller.stop()
    assert not controller.state.control_enabled
    assert not controller.overlay.isVisible()
    assert controller.dock.isVisible()
    assert not controller.dock.permission.isChecked()


def test_capture_hides_both_windows_and_restores_visibility(hud):
    app, controller = hud
    controller.begin_capture(controller.id_for(app.primaryScreen()))
    assert not controller.overlay.isVisible()
    assert not controller.dock.isVisible()
    controller.end_capture()
    assert controller.overlay.isVisible()
    assert controller.dock.isVisible()
    controller.set_annotations_visible(False)
    controller.begin_capture(controller.id_for(app.primaryScreen()))
    controller.end_capture()
    assert not controller.overlay.isVisible()


def test_display_change_invalidates_coordinates_and_permission(hud):
    _, controller = hud
    controller.state.control_enabled = True
    controller._display_changed()
    assert controller.state.tutorial is None
    assert not controller.state.control_enabled
    assert not controller.overlay.isVisible()


def test_cancelled_bridge_request_never_executes_input():
    bridge = GuiBridge()
    late_click = Mock()
    future = Future()
    future.cancel()
    bridge._run(late_click, future)
    late_click.assert_not_called()


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows ABI")
def test_windows_input_structure_and_unicode_without_injection():
    import ctypes

    from computer_tutor.platform import WindowsInput

    backend = WindowsInput()
    assert ctypes.sizeof(backend.Input) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    backend._send = Mock()
    backend.type_text("ü👋")
    events = backend._send.call_args.args[0]
    # ü is one UTF-16 unit; the emoji is a surrogate pair; each has a down/up event.
    assert len(events) == 6
    assert [event.payload.keyboard.flags for event in events] == [4, 6, 4, 6, 4, 6]


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows ABI")
def test_partial_mouse_injection_releases_button():
    from computer_tutor.platform import WindowsInput

    backend = WindowsInput()
    backend.user32 = Mock()
    backend.user32.SendInput.side_effect = [1, 1]
    with pytest.raises(RuntimeError, match="blocked input"):
        backend._send([backend._mouse(0x0002), backend._mouse(0x0004)])
    releases = backend.user32.SendInput.call_args.args[1]
    assert releases[0].payload.mouse.flags == 0x0004
