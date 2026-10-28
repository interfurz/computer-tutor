"""GUI-thread authority for monitor selection, lesson state and input permission."""

import sys
import time
import uuid
from typing import Literal

from PySide6.QtCore import QObject, QRectF, QTimer
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from computer_tutor.models import Step, Tutorial, TutorState
from computer_tutor.platform import StopHotkey, WindowsInput, physical_monitors
from computer_tutor.storage import load_settings
from computer_tutor.ui import AnnotationOverlay, LessonDock


class TutorController(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.instance_id = uuid.uuid4().hex
        self.state = TutorState()
        self.input_backend = None
        self.capture_depth = 0
        self.settings = load_settings()
        self.home = None
        self.tray = None
        self.agent = None
        self.busy = False
        self.generation_error = False
        self.lesson_mode = "external"
        self.lesson_done = False
        self.goal = ""
        self.message = "Bereit für deine nächste Lektion"
        self.dock_visible = True
        self.capture_windows = []
        self.capture_leases = {}
        self.sessions = {}
        self.quitting = False
        self.overlay = AnnotationOverlay()
        self.dock = LessonDock(self)
        self.hotkey = StopHotkey(self.stop)
        app.installNativeEventFilter(self.hotkey)
        app.aboutToQuit.connect(self.hotkey.close)
        app.screenAdded.connect(self._display_changed)
        app.screenRemoved.connect(self._display_changed)
        for screen in app.screens():
            self._watch_screen(screen)
        self.refresh()

    def setup_shell(self, bridge):
        from computer_tutor.agent import LessonAgent
        from computer_tutor.capture import ScreenCapture
        from computer_tutor.home import HomeWindow

        self.agent = LessonAgent(ScreenCapture(bridge, self))
        self.agent.ready.connect(self._generated)
        self.agent.failed.connect(self._generation_failed)
        self.agent.settled.connect(self._generation_settled)
        self.home = HomeWindow(self)
        self.dock_visible = False
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self.app.windowIcon(), self)
            self.tray.setToolTip("Computer Tutor")
            menu = QMenu()
            menu.addAction("Computer Tutor öffnen", self.show_home)
            menu.addAction("Lernleiste anzeigen", self.show_dock)
            menu.addAction("Stopp", self.stop)
            menu.addSeparator()
            menu.addAction("Beenden", self.quit)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(
                lambda reason: (
                    self.show_home() if reason == QSystemTrayIcon.ActivationReason.Trigger else None
                )
            )
            self.tray.show()
            self.tray_menu = menu
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self._expire_sessions)
        self.session_timer.start(2000)
        self.refresh()

    def show_home(self):
        if self.home and not self.capture_depth:
            self.home.reload_monitors()
            self.home.show()
            self.home.raise_()
            self.home.activateWindow()
        return {"shown": True}

    def show_dock(self):
        self.dock_visible = True
        self.refresh()

    def start_demo(self):
        from computer_tutor.demo import demo_tutorial

        self.load(demo_tutorial(self.id_for(self.screen())))
        self.lesson_mode = "demo"
        self.message = "Demo · Beispielbereiche auf deinem Desktop"
        if self.home:
            self.home.hide()
        self.refresh()

    def hide_dock(self):
        self.stop()
        self.dock_visible = False
        self.refresh()
        if not self.tray:
            self.show_home()

    def _watch_screen(self, screen):
        screen.setProperty("tutor_watched", True)
        screen.geometryChanged.connect(self._display_changed)
        screen.logicalDotsPerInchChanged.connect(self._display_changed)

    def _display_changed(self, *_args):
        for screen in self.app.screens():
            if not screen.property("tutor_watched"):
                self._watch_screen(screen)
        # Old coordinates may now point at a different control. Require a new tutorial.
        self.state.stop()
        self.state.tutorial = None
        if self.agent:
            self.agent.cancel()
        self.busy = False
        self.message = "Bildschirm geändert. Bitte das Tutorial neu starten."
        self.dock.reset_position()
        self.refresh()

    def screen(self, monitor_id=None):
        if monitor_id is None and self.state.tutorial:
            monitor_id = self.state.tutorial.monitor_id
        if monitor_id is None:
            return self.app.primaryScreen()
        for screen in self.app.screens():
            if self.id_for(screen) == monitor_id:
                return screen
        raise ValueError(f"Monitor {monitor_id!r} is no longer connected. List monitors again.")

    def id_for(self, screen):
        return screen.name() or f"display-{self.app.screens().index(screen)}"

    def monitors(self):
        physical = physical_monitors()
        result = []
        for screen in self.app.screens():
            geometry = screen.geometry()
            bounds = physical.get(screen.name())
            if sys.platform != "win32":
                dpr = screen.devicePixelRatio()
                bounds = (
                    round(geometry.x() * dpr),
                    round(geometry.y() * dpr),
                    round(geometry.width() * dpr),
                    round(geometry.height() * dpr),
                )
            result.append(
                {
                    "id": self.id_for(screen),
                    "primary": screen == self.app.primaryScreen(),
                    "logical_bounds": {
                        "x": geometry.x(),
                        "y": geometry.y(),
                        "width": geometry.width(),
                        "height": geometry.height(),
                    },
                    "physical_bounds": dict(
                        zip(("left", "top", "width", "height"), bounds, strict=True)
                    )
                    if bounds
                    else None,
                    "device_pixel_ratio": screen.devicePixelRatio(),
                }
            )
        return result

    def monitor(self, monitor_id):
        selected_id = self.id_for(self.screen(monitor_id))
        return next(item for item in self.monitors() if item["id"] == selected_id)

    def refresh(self):
        screen = self.screen()
        if screen is None:
            return
        self.dock.render(self.state, screen, self.hotkey.registered)
        self.dock.update_session(self)
        self.dock.apply_text_size(self.settings.font_size)
        self.overlay.setGeometry(screen.geometry())
        self.overlay.step = self.state.step
        self.overlay.panel_rect = QRectF(
            self.dock.geometry().translated(-screen.geometry().topLeft())
        )
        self.overlay.update()
        if self.capture_depth:
            self.overlay.hide()
            self.dock.hide()
        else:
            self.overlay.setVisible(
                self.dock_visible and self.state.annotations_visible and self.state.step is not None
            )
            self.dock.setVisible(self.dock_visible)
            self.dock.raise_()
        if self.home:
            status = (
                "KI erstellt den nächsten Schritt …"
                if self.busy
                else f"{len(self.sessions)} MCP-Agent(en) verbunden"
                if self.sessions
                else self.message
            )
            self.home.connection_status.setText(status)
            self.home.start.setEnabled(not self.busy)

    def load(self, tutorial: Tutorial):
        tutorial = Tutorial.model_validate(tutorial)
        self.screen(tutorial.monitor_id)  # Reject before changing the current lesson.
        if self.agent:
            self.agent.cancel()
        self.busy = False
        self.lesson_mode = "external"
        self.lesson_done = False
        self.dock_visible = True
        if self.home:
            self.home.hide()
            self.capture_windows = [
                window for window in self.capture_windows if window != self.home
            ]
        self.state.load(tutorial)
        self.state.control_enabled = False
        self.refresh()
        return self.snapshot()

    def replace_step(self, step: Step):
        step = Step.model_validate(step)
        if self.state.tutorial is None:
            raise ValueError("Load a tutorial first.")
        self.state.tutorial.steps[self.state.step_index] = step
        self.state.revision += 1
        self.refresh()
        return self.snapshot()

    def navigate(self, direction: Literal["previous", "next"]):
        self.state.navigate(direction)
        self.refresh()
        return self.snapshot()

    def navigate_user(self, direction):
        if self.busy:
            return
        if (
            direction == "next"
            and self.lesson_mode == "direct"
            and not self.lesson_done
            and self.state.tutorial
            and self.state.step_index == len(self.state.tutorial.steps) - 1
        ):
            self._generate()
        else:
            self.navigate(direction)

    def toggle_annotations(self):
        self.set_annotations_visible(not self.state.annotations_visible)

    def set_annotations_visible(self, visible: bool):
        self.state.annotations_visible = visible
        self.state.revision += 1
        self.refresh()
        return self.snapshot()

    def set_control(self, enabled: bool):
        # Connected only to the local checkbox; intentionally absent from MCP tools.
        self.state.control_enabled = enabled and sys.platform == "win32"
        self.state.revision += 1
        self.refresh()

    def stop(self):
        if self.agent:
            self.agent.cancel()
        self.busy = False
        self.message = "Gestoppt. Du kannst dein Tutorial fortsetzen oder neu beginnen."
        self.state.stop()
        self.refresh()
        return self.snapshot()

    def begin_capture(self, monitor_id):
        monitor = self.monitor(monitor_id)
        if not monitor["physical_bounds"]:
            raise RuntimeError("Cannot match this display to Windows physical coordinates.")
        if not self.capture_depth:
            self.capture_windows = [
                widget
                for widget in self.app.topLevelWidgets()
                if widget not in (self.overlay, self.dock) and widget.isVisible()
            ]
            for widget in self.capture_windows:
                widget.hide()
        lease = uuid.uuid4().hex
        self.capture_leases[lease] = time.monotonic()
        self.capture_depth = len(self.capture_leases)
        self.refresh()
        return {**monitor, "capture_token": lease}

    def capture_valid(self, token):
        return token in self.capture_leases

    def end_capture(self, token=None):
        if token is None:
            self.capture_leases.clear()
        else:
            self.capture_leases.pop(token, None)
        self.capture_depth = len(self.capture_leases)
        if not self.capture_depth and not self.quitting:
            for widget in self.capture_windows:
                widget.show()
            self.capture_windows = []
        self.refresh()

    def desktop_action(self, action: str, **arguments):
        if not self.state.control_enabled:
            raise PermissionError("Enable 'Agent darf Maus & Tastatur steuern' in the local HUD.")
        if self.capture_depth:
            raise RuntimeError("Wait for the current screen capture to finish.")
        if action not in {"click", "type_text", "hotkey", "scroll"}:
            raise ValueError("Unknown desktop action")
        own_windows = [w for w in self.app.topLevelWidgets() if w.isVisible()]
        if action != "click" and any(w.isActiveWindow() for w in own_windows):
            raise RuntimeError("Focus the target application first; the tutor HUD has focus.")
        if action == "click":
            monitor = self.monitor(arguments.pop("monitor_id"))
            bounds = monitor["physical_bounds"]
            if not bounds:
                raise RuntimeError("Physical display coordinates are unavailable.")
            x, y = arguments.pop("x"), arguments.pop("y")
            geometry = self.screen(monitor["id"]).geometry()
            logical_x = geometry.x() + round(x * (geometry.width() - 1))
            logical_y = geometry.y() + round(y * (geometry.height() - 1))
            if any(
                w != self.overlay and w.geometry().contains(logical_x, logical_y)
                for w in own_windows
            ):
                raise ValueError("Agent clicks on Computer Tutor's own controls are blocked.")
            arguments["x"] = bounds["left"] + round(x * (bounds["width"] - 1))
            arguments["y"] = bounds["top"] + round(y * (bounds["height"] - 1))
        if self.input_backend is None:
            self.input_backend = WindowsInput()
        getattr(self.input_backend, action)(**arguments)
        return {"executed": action, "verification_required": True}

    def quit(self):
        self.quitting = True
        self.stop()
        if self.tray:
            self.tray.hide()
        QTimer.singleShot(50, self.app.quit)
        return {"quitting": True}

    def snapshot(self):
        return {
            **self.state.snapshot(),
            "busy": self.busy,
            "lesson_mode": self.lesson_mode,
            "lesson_done": self.lesson_done,
            "message": self.message,
            "connected_agents": len(self.sessions),
        }

    def start_learning(self, goal, monitor_id):
        if not self.settings.screen_sharing:
            raise ValueError(
                "Bitte die Bildschirmfreigabe unter KI-Verbindung erlauben und speichern."
            )
        from urllib.parse import urlparse

        key = self.settings.api_key()
        if not key and urlparse(self.settings.endpoint).hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Bitte zuerst einen API-Key unter KI-Verbindung speichern.")
        self.screen(monitor_id)
        self.stop()
        self.goal = goal
        self.lesson_mode = "direct"
        self.lesson_done = False
        self.state.tutorial = None
        self.settings.monitor_id = monitor_id
        self.dock_visible = True
        self.state.annotations_visible = True
        if self.home:
            self.home.hide()
        self._generate()

    def _generate(self):
        if self.busy or not self.agent:
            return
        self.busy = True
        self.generation_error = False
        self.message = "KI erstellt den nächsten Schritt …"
        self.state.annotations_visible = False
        history = [s.model_dump() for s in self.state.tutorial.steps] if self.state.tutorial else []
        self.agent.generate(
            self.settings.model_copy(deep=True),
            self.settings.api_key(),
            self.goal,
            history,
            self.settings.monitor_id,
        )
        self.refresh()

    def _generated(self, generated, cancellation):
        if cancellation.is_set() or cancellation is not self.agent.cancelled:
            return
        step = Step.model_validate(generated.model_dump(exclude={"done"}))
        if self.state.tutorial:
            if len(self.state.tutorial.steps) >= 100:
                self._generation_failed(
                    "100 Schritte erreicht. Bitte eine neue Lektion starten.", cancellation
                )
                return
            self.state.tutorial.steps.append(step)
            self.state.step_index = len(self.state.tutorial.steps) - 1
        else:
            self.state.load(
                Tutorial(title=self.goal[:160], monitor_id=self.settings.monitor_id, steps=[step])
            )
        self.lesson_done = generated.done
        self.state.annotations_visible = True
        self.state.revision += 1
        self.message = "Lernziel erreicht" if generated.done else "Dein nächster Schritt ist bereit"
        self.busy = False
        self.refresh()

    def _generation_failed(self, message, cancellation):
        if cancellation.is_set() or cancellation is not self.agent.cancelled:
            return
        self.message = message
        self.generation_error = True
        self.busy = False
        self.dock.session_message.setText(message)
        self.dock.retry.setVisible(True)
        if self.home:
            self.home.error.setText(message)
        self.refresh()

    def _generation_settled(self, cancellation):
        if cancellation is self.agent.cancelled:
            self.busy = False
            self.refresh()

    def import_tutorial(self, content, monitor_id):
        tutorial = Tutorial.model_validate_json(content)
        tutorial.monitor_id = monitor_id
        self.load(tutorial)
        if self.home:
            self.home.hide()

    def _expire_sessions(self):
        for token, started in list(self.capture_leases.items()):
            if time.monotonic() - started > 10:
                self.end_capture(token)
        expired = [key for key, seen in self.sessions.items() if time.monotonic() - seen > 12]
        for key in expired:
            self.sessions.pop(key, None)
        if expired:
            self.stop()
            self.message = "Agentenverbindung unterbrochen. Eingaben wurden gesperrt."
            self.refresh()

    def rpc(self, method, args, kwargs):
        if method == "ping":
            return {"running": True, "instance_id": self.instance_id}
        if method == "connect_agent":
            first_connection = not self.sessions
            self.sessions[args[0]] = time.monotonic()
            if first_connection and not self.state.tutorial:
                self.dock_visible = True
                self.message = "MCP-Agent verbunden. Warte auf dein Lernziel."
            self.refresh()
            return {"connected": True}
        if method == "disconnect_agent":
            self.sessions.pop(args[0], None)
            self.stop()
            return {"disconnected": True}
        return getattr(self, method)(*args, **kwargs)
