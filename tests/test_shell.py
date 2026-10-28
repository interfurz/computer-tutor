import threading
import time
from unittest.mock import Mock

import pytest

from computer_tutor.agent import GeneratedStep
from computer_tutor.bridge import GuiBridge
from computer_tutor.controller import TutorController
from computer_tutor.models import Annotation, Rect, Step, Tutorial
from computer_tutor.storage import Settings


@pytest.fixture
def shell(qt_app):
    controller = TutorController(qt_app)
    controller.setup_shell(GuiBridge())
    yield controller
    controller.stop()
    controller.session_timer.stop()
    controller.hotkey.close()
    qt_app.removeNativeEventFilter(controller.hotkey)
    if controller.tray:
        controller.tray.hide()
    controller.home.hide()
    controller.dock.hide()
    controller.overlay.hide()


def test_no_screen_is_sent_without_local_consent(shell):
    shell.agent.generate = Mock()
    with pytest.raises(ValueError, match="Bildschirmfreigabe"):
        shell.start_learning("PDF exportieren", shell.id_for(shell.screen()))
    shell.agent.generate.assert_not_called()


def test_direct_lesson_navigation_and_cancelled_result(shell):
    shell.settings = Settings(endpoint="http://localhost:1234/v1", screen_sharing=True)
    shell.agent.generate = Mock()
    shell.start_learning("PDF exportieren", shell.id_for(shell.screen()))
    assert shell.busy
    cancellation = threading.Event()
    shell.agent.cancelled = cancellation
    generated = GeneratedStep(title="Menü öffnen", explanation="Klicke auf Datei.")
    shell._generated(generated, cancellation)
    assert shell.state.step.title == "Menü öffnen"
    assert not shell.busy
    shell.navigate_user("next")
    assert shell.agent.generate.call_count == 2
    shell.stop()
    shell._generated(GeneratedStep(title="Zu spät", explanation="Ignorieren"), cancellation)
    assert shell.state.step.title == "Menü öffnen"
    assert not shell.state.control_enabled


def test_dock_avoids_bottom_target_and_can_collapse(shell):
    shell.load(
        Tutorial(
            title="Test",
            monitor_id=shell.id_for(shell.screen()),
            steps=[
                Step(
                    title="Unten klicken",
                    explanation="Text",
                    annotations=[
                        Annotation(
                            id="bottom",
                            label="Hier",
                            target=Rect(x=0.4, y=0.85, width=0.2, height=0.1),
                        )
                    ],
                ),
            ],
        )
    )
    assert shell.dock.y() < shell.screen().geometry().center().y()
    original = shell.dock.height()
    shell.dock.toggle_compact()
    assert shell.dock.height() < original
    assert shell.dock.explanation.isHidden()


def test_lost_agent_revokes_control_and_recovers_orphan_capture(shell, monkeypatch):
    screen = shell.screen()
    geometry = screen.geometry()
    monkeypatch.setattr(
        "computer_tutor.controller.physical_monitors",
        lambda: {
            screen.name(): (0, 0, geometry.width(), geometry.height()),
        },
    )
    shell.show_dock()
    shell.sessions["lost"] = time.monotonic() - 30
    shell.state.control_enabled = True
    shell.begin_capture(shell.id_for(screen))
    for key in shell.capture_leases:
        shell.capture_leases[key] -= 30
    shell._expire_sessions()
    assert not shell.sessions
    assert not shell.state.control_enabled
    assert not shell.capture_depth
    assert shell.dock.isVisible()


def test_import_rebinds_monitor_and_never_restores_input_permission(shell):
    tutorial = Tutorial(
        title="Saved", monitor_id="disconnected", steps=[Step(title="Test", explanation="Text")]
    )
    shell.import_tutorial(tutorial.model_dump_json(), shell.id_for(shell.screen()))
    assert shell.state.tutorial.monitor_id == shell.id_for(shell.screen())
    assert not shell.state.control_enabled
