"""GUI-thread authority for monitor selection, lesson state and input permission."""

import sys
from typing import Literal

from PySide6.QtCore import QObject, QRectF
from PySide6.QtWidgets import QApplication

from computer_tutor.models import Step, Tutorial, TutorState
from computer_tutor.platform import StopHotkey, WindowsInput, physical_monitors
from computer_tutor.ui import AnnotationOverlay, LessonDock


class TutorController(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.state = TutorState()
        self.input_backend = None
        self.capture_depth = 0
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
            self.overlay.setVisible(self.state.annotations_visible and self.state.step is not None)
            self.dock.show()
            self.dock.raise_()

    def load(self, tutorial: Tutorial):
        self.screen(tutorial.monitor_id)  # Reject before changing the current lesson.
        self.state.load(tutorial)
        self.refresh()
        return self.state.snapshot()

    def replace_step(self, step: Step):
        if self.state.tutorial is None:
            raise ValueError("Load a tutorial first.")
        self.state.tutorial.steps[self.state.step_index] = step
        self.state.revision += 1
        self.refresh()
        return self.state.snapshot()

    def navigate(self, direction: Literal["previous", "next"]):
        self.state.navigate(direction)
        self.refresh()
        return self.state.snapshot()

    def toggle_annotations(self):
        self.set_annotations_visible(not self.state.annotations_visible)

    def set_annotations_visible(self, visible: bool):
        self.state.annotations_visible = visible
        self.state.revision += 1
        self.refresh()
        return self.state.snapshot()

    def set_control(self, enabled: bool):
        # Connected only to the local checkbox; intentionally absent from MCP tools.
        self.state.control_enabled = enabled and sys.platform == "win32"
        self.state.revision += 1
        self.refresh()

    def stop(self):
        self.state.stop()
        self.refresh()
        return self.state.snapshot()

    def begin_capture(self, monitor_id):
        monitor = self.monitor(monitor_id)
        if not monitor["physical_bounds"]:
            raise RuntimeError("Cannot match this display to Windows physical coordinates.")
        self.capture_depth += 1
        self.refresh()
        return monitor

    def end_capture(self):
        self.capture_depth = max(0, self.capture_depth - 1)
        self.refresh()

    def desktop_action(self, action: str, **arguments):
        if not self.state.control_enabled:
            raise PermissionError("Enable 'Agent darf Maus & Tastatur steuern' in the local HUD.")
        if self.capture_depth:
            raise RuntimeError("Wait for the current screen capture to finish.")
        if action != "click" and self.dock.isActiveWindow():
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
            if self.dock.isVisible() and self.dock.geometry().contains(logical_x, logical_y):
                raise ValueError("Agent clicks on Computer Tutor's own controls are blocked.")
            arguments["x"] = bounds["left"] + round(x * (bounds["width"] - 1))
            arguments["y"] = bounds["top"] + round(y * (bounds["height"] - 1))
        if self.input_backend is None:
            self.input_backend = WindowsInput()
        getattr(self.input_backend, action)(**arguments)
        return {"executed": action, "verification_required": True}

    def quit(self):
        self.state.stop()
        self.app.quit()
